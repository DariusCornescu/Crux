package com.darius.splitrail.data.repository

import android.util.Log
import com.darius.splitrail.data.model.IntegrationsStatus
import com.darius.splitrail.network.RetrofitClient
import com.darius.splitrail.network.SplitrailApi
import com.darius.splitrail.network.toModel
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

class IntegrationsRepository(private val api: SplitrailApi = RetrofitClient.api) {

    companion object { const val TAG = "IntegrationsRepository" }

    suspend fun getStatus(): RepoResult<IntegrationsStatus> = withContext(Dispatchers.IO) {
        try {
            val response = api.getIntegrationsStatus()
            if (response.isSuccessful && response.body() != null) {
                RepoResult.Success(response.body()!!.toModel())
            } else {
                RepoResult.Error("SERVER ${response.code()}")
            }
        } catch (e: Exception) {
            Log.e(TAG, "Network error: ${e.message}")
            RepoResult.Error("NO SIGNAL — ${e.message ?: "network error"}")
        }
    }

    /** Returns the provider's OAuth page URL; the screen opens it in the browser. */
    suspend fun getAuthorizeUrl(provider: String): RepoResult<String> = withContext(Dispatchers.IO) {
        try {
            val response = api.getAuthorizeUrl(provider)
            if (response.isSuccessful && response.body() != null) {
                RepoResult.Success(response.body()!!.authorize_url)
            } else {
                RepoResult.Error("SERVER ${response.code()}")
            }
        } catch (e: Exception) {
            RepoResult.Error("NO SIGNAL — ${e.message ?: "network error"}")
        }
    }

    suspend fun triggerSync(provider: String): RepoResult<Int> = withContext(Dispatchers.IO) {
        try {
            val response = api.triggerSync(provider)
            if (response.isSuccessful && response.body() != null) {
                RepoResult.Success(response.body()!!.synced)
            } else {
                RepoResult.Error("SERVER ${response.code()}")
            }
        } catch (e: Exception) {
            RepoResult.Error("NO SIGNAL — ${e.message ?: "network error"}")
        }
    }
}
