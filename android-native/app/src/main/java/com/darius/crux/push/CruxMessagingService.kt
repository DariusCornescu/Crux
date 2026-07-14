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
 * the app is backgrounded; this handles the foreground case and routes by
 * message `type` (report vs meeting) to its own channel.
 */
class CruxMessagingService : FirebaseMessagingService() {

    companion object {
        const val TAG = "CruxFCM"
        const val CHANNEL_REPORTS = "reports"
        const val CHANNEL_MEETINGS = "meetings"
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

        val isMeeting = message.data["type"] == "meeting"
        val channelId = if (isMeeting) CHANNEL_MEETINGS else CHANNEL_REPORTS
        val channelName = if (isMeeting) "Meeting reminders" else "Weekly reports"
        manager.createNotificationChannel(
            NotificationChannel(channelId, channelName, NotificationManager.IMPORTANCE_DEFAULT),
        )

        val notifId = (message.data["event_id"] ?: message.data["report_id"])?.toIntOrNull()
            ?: message.messageId?.hashCode() ?: 1

        try {
            manager.notify(
                notifId,
                NotificationCompat.Builder(this, channelId)
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
