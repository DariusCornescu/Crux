package com.darius.splitrail.push

import android.util.Log
import com.darius.splitrail.data.repository.DeviceRepository
import com.google.firebase.messaging.FirebaseMessaging
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch

/**
 * Registers this device's FCM token with the backend. Guarded so the app is
 * a clean no-op while Firebase isn't configured (no google-services.json).
 */
object PushRegistrar {

    private const val TAG = "PushRegistrar"

    fun register() {
        runCatching {
            FirebaseMessaging.getInstance().token.addOnSuccessListener { token ->
                CoroutineScope(Dispatchers.IO).launch {
                    DeviceRepository().registerToken(token)
                }
            }
        }.onFailure {
            Log.i(TAG, "Firebase not configured yet — push disabled (${it.message})")
        }
    }
}
