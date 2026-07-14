package com.darius.crux.data.health

import android.content.Context
import android.util.Log
import androidx.health.connect.client.HealthConnectClient
import androidx.health.connect.client.permission.HealthPermission
import androidx.health.connect.client.records.HeartRateVariabilityRmssdRecord
import androidx.health.connect.client.records.RestingHeartRateRecord
import androidx.health.connect.client.records.SleepSessionRecord
import androidx.health.connect.client.request.ReadRecordsRequest
import androidx.health.connect.client.time.TimeRangeFilter
import com.darius.crux.network.RetrofitClient
import com.darius.crux.network.WellnessBatchDTO
import com.darius.crux.network.WellnessSampleDTO
import java.time.Duration
import java.time.Instant
import java.time.temporal.ChronoUnit

/**
 * Reads sleep, resting HR and HRV from Health Connect and posts them to the
 * backend wellness ingest (source = health_connect), which rolls up into the
 * DailySummary behind CONDITIONS + readiness. A no-op when Health Connect is
 * unavailable or its permissions aren't granted.
 */
class HealthConnectManager(private val context: Context) {

    companion object {
        const val TAG = "HealthConnect"
        val PERMISSIONS = setOf(
            HealthPermission.getReadPermission(SleepSessionRecord::class),
            HealthPermission.getReadPermission(RestingHeartRateRecord::class),
            HealthPermission.getReadPermission(HeartRateVariabilityRmssdRecord::class),
        )
    }

    fun available(): Boolean =
        HealthConnectClient.getSdkStatus(context) == HealthConnectClient.SDK_AVAILABLE

    suspend fun hasPermissions(): Boolean =
        available() && runCatching {
            HealthConnectClient.getOrCreate(context)
                .permissionController.getGrantedPermissions().containsAll(PERMISSIONS)
        }.getOrDefault(false)

    /** Read the last [days] of health data and post samples. Returns #ingested, or -1 on failure. */
    suspend fun sync(days: Long = 14): Int {
        if (!available()) return -1
        val client = HealthConnectClient.getOrCreate(context)
        val granted = runCatching { client.permissionController.getGrantedPermissions() }.getOrNull()
        if (granted == null || !granted.containsAll(PERMISSIONS)) return -1

        val end = Instant.now()
        val range = TimeRangeFilter.between(end.minus(days, ChronoUnit.DAYS), end)
        val samples = mutableListOf<WellnessSampleDTO>()

        runCatching {
            client.readRecords(ReadRecordsRequest(SleepSessionRecord::class, range)).records.forEach { s ->
                val minutes = Duration.between(s.startTime, s.endTime).toMinutes()
                if (minutes > 0) {
                    samples.add(WellnessSampleDTO(s.endTime.toString(), "sleep_minutes", minutes.toDouble()))
                }
            }
        }.onFailure { Log.w(TAG, "sleep read: ${it.message}") }

        runCatching {
            client.readRecords(ReadRecordsRequest(RestingHeartRateRecord::class, range)).records.forEach { r ->
                samples.add(WellnessSampleDTO(r.time.toString(), "resting_hr", r.beatsPerMinute.toDouble()))
            }
        }.onFailure { Log.w(TAG, "rhr read: ${it.message}") }

        runCatching {
            client.readRecords(ReadRecordsRequest(HeartRateVariabilityRmssdRecord::class, range)).records.forEach { h ->
                samples.add(WellnessSampleDTO(h.time.toString(), "hrv_ms", h.heartRateVariabilityMillis))
            }
        }.onFailure { Log.w(TAG, "hrv read: ${it.message}") }

        if (samples.isEmpty()) return 0
        return runCatching {
            val resp = RetrofitClient.api.ingestWellness(WellnessBatchDTO(samples))
            if (resp.isSuccessful) resp.body()?.ingested ?: 0 else -1
        }.getOrDefault(-1)
    }
}
