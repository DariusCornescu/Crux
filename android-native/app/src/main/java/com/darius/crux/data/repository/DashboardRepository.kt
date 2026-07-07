package com.darius.crux.data.repository

import android.util.Log
import com.darius.crux.data.model.DashboardData
import com.darius.crux.network.RetrofitClient
import com.darius.crux.network.CruxApi
import com.darius.crux.network.toModel
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

class DashboardRepository(private val api: CruxApi = RetrofitClient.api) {

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
