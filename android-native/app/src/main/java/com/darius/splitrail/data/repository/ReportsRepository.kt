package com.darius.splitrail.data.repository

import android.util.Log
import com.darius.splitrail.data.model.Report
import com.darius.splitrail.network.RetrofitClient
import com.darius.splitrail.network.SplitrailApi
import com.darius.splitrail.network.toModel
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

class ReportsRepository(private val api: SplitrailApi = RetrofitClient.api) {

    companion object { const val TAG = "ReportsRepository" }

    suspend fun getReports(): RepoResult<List<Report>> = withContext(Dispatchers.IO) {
        try {
            val response = api.getReports()
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

    suspend fun getReport(id: Long): RepoResult<Report> = withContext(Dispatchers.IO) {
        try {
            val response = api.getReport(id)
            if (response.isSuccessful && response.body() != null) {
                RepoResult.Success(response.body()!!.toModel())
            } else {
                RepoResult.Error("SERVER ${response.code()}")
            }
        } catch (e: Exception) {
            RepoResult.Error("NO SIGNAL — ${e.message ?: "network error"}")
        }
    }

    /** Manual trigger of the weekly generation (same path the Monday beat runs). */
    suspend fun generateReport(): RepoResult<Report> = withContext(Dispatchers.IO) {
        try {
            val response = api.generateReport()
            if (response.isSuccessful && response.body() != null) {
                RepoResult.Success(response.body()!!.toModel())
            } else {
                RepoResult.Error("SERVER ${response.code()}")
            }
        } catch (e: Exception) {
            RepoResult.Error("NO SIGNAL — ${e.message ?: "network error"}")
        }
    }
}
