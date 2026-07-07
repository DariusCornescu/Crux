package com.darius.crux.data.repository

import android.util.Log
import com.darius.crux.data.model.IntegrationsStatus
import com.darius.crux.network.RetrofitClient
import com.darius.crux.network.CruxApi
import com.darius.crux.network.toModel
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

class IntegrationsRepository(private val api: CruxApi = RetrofitClient.api) {

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
