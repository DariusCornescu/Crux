package com.darius.crux.data.repository

import android.util.Log
import com.darius.crux.network.DeviceRegisterDTO
import com.darius.crux.network.RetrofitClient
import com.darius.crux.network.CruxApi
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

class DeviceRepository(private val api: CruxApi = RetrofitClient.api) {

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
