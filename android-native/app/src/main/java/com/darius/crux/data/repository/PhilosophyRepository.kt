package com.darius.crux.data.repository

import android.util.Log
import com.darius.crux.network.CruxApi
import com.darius.crux.network.QuoteDTO
import com.darius.crux.network.ReflectionDTO
import com.darius.crux.network.RetrofitClient
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

/** Philosophy zone: today's quote + reflection and the scrollable quote archive. */
class PhilosophyRepository(private val api: CruxApi = RetrofitClient.api) {

    companion object { const val TAG = "PhilosophyRepository" }

    suspend fun getQuoteToday(): RepoResult<QuoteDTO> = withContext(Dispatchers.IO) {
        try {
            val response = api.getQuoteToday()
            if (response.isSuccessful && response.body() != null) {
                RepoResult.Success(response.body()!!)
            } else {
                RepoResult.Error("SERVER ${response.code()}")
            }
        } catch (e: Exception) {
            Log.e(TAG, "quote error: ${e.message}")
            RepoResult.Error("NO SIGNAL — ${e.message ?: "network error"}")
        }
    }

    suspend fun getReflectionToday(): RepoResult<ReflectionDTO> = withContext(Dispatchers.IO) {
        try {
            val response = api.getReflectionToday()
            if (response.isSuccessful && response.body() != null) {
                RepoResult.Success(response.body()!!)
            } else {
                RepoResult.Error("SERVER ${response.code()}")
            }
        } catch (e: Exception) {
            Log.e(TAG, "reflection error: ${e.message}")
            RepoResult.Error("NO SIGNAL — ${e.message ?: "network error"}")
        }
    }

    suspend fun getQuoteArchive(limit: Int = 30): RepoResult<List<QuoteDTO>> = withContext(Dispatchers.IO) {
        try {
            val response = api.getQuoteArchive(limit)
            if (response.isSuccessful && response.body() != null) {
                RepoResult.Success(response.body()!!)
            } else {
                RepoResult.Error("SERVER ${response.code()}")
            }
        } catch (e: Exception) {
            Log.e(TAG, "archive error: ${e.message}")
            RepoResult.Error("NO SIGNAL — ${e.message ?: "network error"}")
        }
    }
}
