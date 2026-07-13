package com.darius.crux.data.repository

import android.util.Log
import com.darius.crux.network.CruxApi
import com.darius.crux.network.GithubHeatmapDTO
import com.darius.crux.network.RetrofitClient
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

/** GitHub contribution heatmap — coding as another discipline. */
class GithubRepository(private val api: CruxApi = RetrofitClient.api) {

    companion object { const val TAG = "GithubRepository" }

    suspend fun getHeatmap(weeks: Int = 53): RepoResult<GithubHeatmapDTO> = withContext(Dispatchers.IO) {
        try {
            val response = api.getGithubHeatmap(weeks)
            if (response.isSuccessful && response.body() != null) {
                RepoResult.Success(response.body()!!)
            } else {
                RepoResult.Error("SERVER ${response.code()}")
            }
        } catch (e: Exception) {
            Log.e(TAG, "heatmap error: ${e.message}")
            RepoResult.Error("NO SIGNAL — ${e.message ?: "network error"}")
        }
    }
}
