package com.darius.crux.data.repository

import android.util.Log
import com.darius.crux.network.CruxApi
import com.darius.crux.network.ObjectiveDTO
import com.darius.crux.network.ObjectiveInDTO
import com.darius.crux.network.RetrofitClient
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

/** Summit objective — the single active training goal. */
class ObjectiveRepository(private val api: CruxApi = RetrofitClient.api) {

    companion object { const val TAG = "ObjectiveRepository" }

    /** Current objective, or Success(null) when none is set (200 with a null body). */
    suspend fun getCurrent(): RepoResult<ObjectiveDTO?> = withContext(Dispatchers.IO) {
        try {
            val response = api.getObjective()
            if (response.isSuccessful) {
                RepoResult.Success(response.body())
            } else {
                RepoResult.Error("SERVER ${response.code()}")
            }
        } catch (e: Exception) {
            Log.e(TAG, "objective error: ${e.message}")
            RepoResult.Error("NO SIGNAL — ${e.message ?: "network error"}")
        }
    }

    suspend fun save(body: ObjectiveInDTO): RepoResult<ObjectiveDTO> = withContext(Dispatchers.IO) {
        try {
            val response = api.setObjective(body)
            if (response.isSuccessful && response.body() != null) {
                RepoResult.Success(response.body()!!)
            } else {
                RepoResult.Error("SERVER ${response.code()}")
            }
        } catch (e: Exception) {
            Log.e(TAG, "objective save error: ${e.message}")
            RepoResult.Error("NO SIGNAL — ${e.message ?: "network error"}")
        }
    }
}
