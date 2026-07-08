package com.darius.crux.data.repository

import android.util.Log
import com.darius.crux.network.CruxApi
import com.darius.crux.network.RetrofitClient
import com.darius.crux.network.SignalsDTO
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

class SignalsRepository(private val api: CruxApi = RetrofitClient.api) {

    companion object { const val TAG = "SignalsRepository" }

    suspend fun getSignalsDetail(): RepoResult<SignalsDTO> = withContext(Dispatchers.IO) {
        try {
            val response = api.getSignalsDetail()
            if (response.isSuccessful && response.body() != null) {
                RepoResult.Success(response.body()!!)
            } else {
                Log.w(TAG, "Server error ${response.code()}")
                RepoResult.Error("SERVER ${response.code()}")
            }
        } catch (e: Exception) {
            Log.e(TAG, "Network error: ${e.message}")
            RepoResult.Error("NO SIGNAL — ${e.message ?: "network error"}")
        }
    }
}
