package com.darius.crux.data.repository

import android.util.Log
import com.darius.crux.data.model.DashboardData
import com.darius.crux.network.RetrofitClient
import com.darius.crux.network.CruxApi
import com.darius.crux.network.QuoteDTO
import com.darius.crux.network.UpcomingEventDTO
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

    /** NEXT UP agenda rows — independent of the main dashboard load. */
    suspend fun getUpcomingEvents(): RepoResult<List<UpcomingEventDTO>> = withContext(Dispatchers.IO) {
        try {
            val response = api.getUpcomingEvents()
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

    /** Daily quote line — independent of the main dashboard load. */
    suspend fun getQuoteToday(): RepoResult<QuoteDTO> = withContext(Dispatchers.IO) {
        try {
            val response = api.getQuoteToday()
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
