package com.darius.crux.data.repository

import android.util.Log
import com.darius.crux.network.CalendarEventDTO
import com.darius.crux.network.CruxApi
import com.darius.crux.network.RetrofitClient
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

/** Full meeting record (past + future) for the Meetings screen. */
class CalendarRepository(private val api: CruxApi = RetrofitClient.api) {

    companion object { const val TAG = "CalendarRepository" }

    suspend fun getEvents(from: String? = null, limit: Int = 200): RepoResult<List<CalendarEventDTO>> =
        withContext(Dispatchers.IO) {
            try {
                val response = api.getCalendarEvents(from, limit)
                if (response.isSuccessful && response.body() != null) {
                    RepoResult.Success(response.body()!!)
                } else {
                    RepoResult.Error("SERVER ${response.code()}")
                }
            } catch (e: Exception) {
                Log.e(TAG, "events error: ${e.message}")
                RepoResult.Error("NO SIGNAL — ${e.message ?: "network error"}")
            }
        }
}
