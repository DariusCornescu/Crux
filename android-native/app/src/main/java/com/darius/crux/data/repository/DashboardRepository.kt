package com.darius.crux.data.repository

import android.util.Log
import com.darius.crux.data.model.DashboardData
import com.darius.crux.network.RetrofitClient
import com.darius.crux.network.CruxApi
import com.darius.crux.network.MoodDTO
import com.darius.crux.network.QuoteDTO
import com.darius.crux.network.ReadinessDTO
import com.darius.crux.network.TrainingGridDTO
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

    /** Current music mood phrase — independent of the main dashboard load. */
    suspend fun getMoodCurrent(): RepoResult<MoodDTO> = withContext(Dispatchers.IO) {
        try {
            val response = api.getMoodCurrent()
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

    /** Training contribution grid — independent of the main dashboard load. */
    suspend fun getTrainingGrid(weeks: Int = 20): RepoResult<TrainingGridDTO> = withContext(Dispatchers.IO) {
        try {
            val response = api.getTrainingGrid(weeks)
            if (response.isSuccessful && response.body() != null) {
                RepoResult.Success(response.body()!!)
            } else {
                RepoResult.Error("SERVER ${response.code()}")
            }
        } catch (e: Exception) {
            RepoResult.Error("NO SIGNAL — ${e.message ?: "network error"}")
        }
    }

    /** Today's readiness — independent of the main dashboard load. */
    suspend fun getReadiness(): RepoResult<ReadinessDTO> = withContext(Dispatchers.IO) {
        try {
            val response = api.getReadiness()
            if (response.isSuccessful && response.body() != null) {
                RepoResult.Success(response.body()!!)
            } else {
                RepoResult.Error("SERVER ${response.code()}")
            }
        } catch (e: Exception) {
            RepoResult.Error("NO SIGNAL — ${e.message ?: "network error"}")
        }
    }
}
