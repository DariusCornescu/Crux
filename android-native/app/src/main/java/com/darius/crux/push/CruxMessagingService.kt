package com.darius.crux.push

import android.app.NotificationChannel
import android.app.NotificationManager
import android.util.Log
import androidx.core.app.NotificationCompat
import androidx.core.app.NotificationManagerCompat
import com.darius.crux.R
import com.darius.crux.data.repository.DeviceRepository
import com.google.firebase.messaging.FirebaseMessagingService
import com.google.firebase.messaging.RemoteMessage
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch

/**
 * FCM entry point (build-order step 7).
 *
 * Inert until Firebase is configured: add google-services.json to app/ and
 * uncomment the google-services plugin lines in both build.gradle.kts files
 * (see README). Notification-type FCM messages are shown by the system when
 * the app is backgrounded; this handles the foreground case.
 */
class CruxMessagingService : FirebaseMessagingService() {

    companion object {
        const val TAG = "CruxFCM"
        const val CHANNEL_ID = "reports"
    }

    override fun onNewToken(token: String) {
        Log.d(TAG, "new FCM token")
        CoroutineScope(Dispatchers.IO).launch {
            DeviceRepository().registerToken(token)
        }
    }

    override fun onMessageReceived(message: RemoteMessage) {
        val title = message.notification?.title ?: "CRUX"
        val body = message.notification?.body ?: return

        val manager = NotificationManagerCompat.from(this)
        if (!manager.areNotificationsEnabled()) return

        val channel = NotificationChannel(
            CHANNEL_ID, "Weekly reports", NotificationManager.IMPORTANCE_DEFAULT)
        manager.createNotificationChannel(channel)

        try {
            manager.notify(
                message.data["report_id"]?.toIntOrNull() ?: 1,
                NotificationCompat.Builder(this, CHANNEL_ID)
                    .setSmallIcon(R.drawable.ic_launcher_foreground)
                    .setContentTitle(title)
                    .setContentText(body)
                    .setAutoCancel(true)
                    .build(),
            )
        } catch (e: SecurityException) {
            Log.w(TAG, "notification blocked: ${e.message}")
        }
    }
}
