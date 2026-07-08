package com.darius.crux.data.repository

import android.util.Log
import com.darius.crux.data.model.ChatMessage
import com.darius.crux.network.ApiConfig
import com.darius.crux.network.ChatRequestDTO
import com.darius.crux.network.RetrofitClient
import com.darius.crux.network.CruxApi
import com.darius.crux.network.toModel
import com.google.gson.Gson
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.channels.awaitClose
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.callbackFlow
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.RequestBody.Companion.toRequestBody
import okhttp3.Request
import java.io.IOException
import java.util.concurrent.TimeUnit

class ChatRepository(private val api: CruxApi = RetrofitClient.api) {

    companion object { const val TAG = "ChatRepository" }

    private val gson = Gson()

    // Dedicated client with a longer read timeout for the token-by-token SSE stream —
    // derived from the shared client so interceptors/other timeouts stay in sync.
    private val streamingClient by lazy {
        RetrofitClient.okHttpClient.newBuilder()
            .readTimeout(120, TimeUnit.SECONDS)
            .build()
    }

    private data class StreamTokenDTO(val t: String?)

    suspend fun getHistory(): RepoResult<List<ChatMessage>> = withContext(Dispatchers.IO) {
        try {
            val response = api.getChatHistory()
            if (response.isSuccessful && response.body() != null) {
                RepoResult.Success(response.body()!!.map { it.toModel() })
            } else {
                RepoResult.Error("SERVER ${response.code()}")
            }
        } catch (e: Exception) {
            Log.e(TAG, "Network error: ${e.message}")
            RepoResult.Error("NO SIGNAL — ${e.message ?: "network error"}")
        }
    }

    suspend fun send(message: String): RepoResult<String> = withContext(Dispatchers.IO) {
        try {
            val response = api.sendChatMessage(ChatRequestDTO(message))
            if (response.isSuccessful && response.body() != null) {
                RepoResult.Success(response.body()!!.reply)
            } else {
                RepoResult.Error("SERVER ${response.code()}")
            }
        } catch (e: Exception) {
            RepoResult.Error("NO SIGNAL — ${e.message ?: "network error"}")
        }
    }

    suspend fun clearHistory(): RepoResult<Unit> = withContext(Dispatchers.IO) {
        try {
            val response = api.clearChatHistory()
            if (response.isSuccessful) {
                RepoResult.Success(Unit)
            } else {
                RepoResult.Error("SERVER ${response.code()}")
            }
        } catch (e: Exception) {
            RepoResult.Error("NO SIGNAL — ${e.message ?: "network error"}")
        }
    }

    /**
     * Streams assistant tokens from `POST chat/stream` (SSE). Raw OkHttp — Retrofit has no
     * first-class SSE support. The blocking read loop runs in a child coroutine on
     * Dispatchers.IO; `awaitClose { call.cancel() }` runs as soon as the collector stops
     * (cancellation included), aborting the socket and unblocking `readUtf8Line()`
     * immediately instead of leaving it hanging until the 120s read timeout.
     */
    fun streamMessage(message: String): Flow<String> = callbackFlow {
        val requestBody = gson.toJson(mapOf("message" to message))
            .toRequestBody("application/json".toMediaType())
        val request = Request.Builder()
            .url(ApiConfig.BASE_URL + "chat/stream")
            .post(requestBody)
            .build()
        val call = streamingClient.newCall(request)

        launch(Dispatchers.IO) {
            try {
                call.execute().use { response ->
                    if (!response.isSuccessful) {
                        throw IOException("SERVER ${response.code}")
                    }
                    val source = response.body!!.source()
                    while (true) {
                        val line = source.readUtf8Line() ?: break // EOF without [DONE] — end normally
                        if (!line.startsWith("data: ")) continue
                        val payload = line.removePrefix("data: ")
                        if (payload == "[DONE]") break
                        val token = runCatching { gson.fromJson(payload, StreamTokenDTO::class.java)?.t }
                            .getOrNull()
                        if (!token.isNullOrEmpty()) send(token) // suspends if the collector lags
                    }
                }
                close()
            } catch (e: Exception) {
                close(e) // no-op if the flow is already closing (e.g. read aborted by cancel)
            }
        }

        awaitClose { call.cancel() }
    }
}
