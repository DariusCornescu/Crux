package com.darius.splitrail.data.repository

import android.util.Log
import com.darius.splitrail.network.DeviceRegisterDTO
import com.darius.splitrail.network.RetrofitClient
import com.darius.splitrail.network.SplitrailApi
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

class DeviceRepository(private val api: SplitrailApi = RetrofitClient.api) {

    companion object { const val TAG = "DeviceRepository" }

    /** Idempotent — safe to call on every token refresh. */
    suspend fun registerToken(token: String): Boolean = withContext(Dispatchers.IO) {
        try {
            api.registerDevice(DeviceRegisterDTO(token)).isSuccessful
        } catch (e: Exception) {
            Log.w(TAG, "token registration failed: ${e.message}")
            false
        }
    }
}
