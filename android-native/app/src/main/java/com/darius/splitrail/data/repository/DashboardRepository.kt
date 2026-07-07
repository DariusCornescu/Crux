package com.darius.splitrail.data.repository

import android.util.Log
import com.darius.splitrail.data.model.DashboardData
import com.darius.splitrail.network.RetrofitClient
import com.darius.splitrail.network.SplitrailApi
import com.darius.splitrail.network.toModel
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

class DashboardRepository(private val api: SplitrailApi = RetrofitClient.api) {

    companion object { const val TAG = "DashboardRepository" }

    suspend fun getDashboard(): RepoResult<DashboardData> = withContext(Dispatchers.IO) {
        try {
            val response = api.getDashboard()
            if (response.isSuccessful && response.body() != null) {
                RepoResult.Success(response.body()!!.toModel())
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
