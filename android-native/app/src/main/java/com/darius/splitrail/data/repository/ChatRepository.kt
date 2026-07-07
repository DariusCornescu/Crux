package com.darius.splitrail.data.repository

import android.util.Log
import com.darius.splitrail.data.model.ChatMessage
import com.darius.splitrail.network.ChatRequestDTO
import com.darius.splitrail.network.RetrofitClient
import com.darius.splitrail.network.SplitrailApi
import com.darius.splitrail.network.toModel
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

class ChatRepository(private val api: SplitrailApi = RetrofitClient.api) {

    companion object { const val TAG = "ChatRepository" }

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
}
