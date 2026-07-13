package com.darius.crux.network

import com.darius.crux.data.model.AltiBlock
import com.darius.crux.data.model.Conditions
import com.darius.crux.data.model.DashboardData
import com.darius.crux.data.model.EffortMode
import com.darius.crux.data.model.GateBlock
import com.darius.crux.data.model.IntegrationState
import com.darius.crux.data.model.IntegrationsStatus
import com.darius.crux.data.model.ChatMessage
import com.darius.crux.data.model.RailEntry
import com.darius.crux.data.model.Report
import com.darius.crux.data.model.StripBlock
import java.time.LocalDate
import kotlin.math.roundToInt

// Field names are snake_case on purpose — they mirror the FastAPI JSON payloads
// one-to-one (same convention as ListManagerApp's DTOs.kt).

data class ConditionsDTO(val sleep_min: Int?, val resting_hr: Int?, val mood_valence: Double?)
data class MoodPointDTO(val day: String, val valence: Double?)
data class RailEntryDTO(val day: String, val mode: String, val type: String, val duration_s: Int, val best_split: Double?, val distance_m: Double?, val vert_m: Double?)
data class GateBlockDTO(val best_split: Double?, val session_note: String?, val splits: List<Double>?)
data class StripBlockDTO(val week_km: Double, val long_run_km: Double, val z2_pct: Double?, val pace_trend: List<Double>?)
data class AltiBlockDTO(val vert_m: Double, val goal_m: Double, val load_kg: Double?, val carries: Int)
data class DashboardDTO(val week: Int, val demo: Boolean?, val conditions: ConditionsDTO, val mood_trend: List<MoodPointDTO>?, val rail: List<RailEntryDTO>?, val gate: GateBlockDTO, val strip: StripBlockDTO, val alti: AltiBlockDTO)

data class ReportDTO(val id: Long, val kind: String, val period_start: String, val period_end: String, val body_md: String, val highlights: Map<String, Any?>?, val created_at: String)

data class AuthorizeUrlDTO(val authorize_url: String)
data class IntegrationStateDTO(val connected: Boolean, val athlete_id: String?, val last_synced_at: String?)
data class IntegrationsStatusDTO(
    val strava: IntegrationStateDTO,
    val spotify: IntegrationStateDTO,
    val calendar: IntegrationStateDTO? = null,
    val github: IntegrationStateDTO? = null,
)
data class SyncResultDTO(val synced: Int)

// ---- DTO -> domain mappers (cf. ListManagerApp's toEntity()) ----

private fun dayIndexOf(isoDate: String): Int =
    runCatching { LocalDate.parse(isoDate).dayOfWeek.value - 1 }.getOrDefault(0)

fun RailEntryDTO.toModel() = RailEntry(
    dayIndex = dayIndexOf(day),
    mode = runCatching { EffortMode.valueOf(mode.uppercase()) }.getOrDefault(EffortMode.AEROBIC),
    durationS = duration_s,
    bestSplit = best_split,
    distanceM = distance_m,
    vertM = vert_m,
)

fun DashboardDTO.toModel() = DashboardData(
    week = week,
    isDemo = demo == true,
    conditions = Conditions(conditions.sleep_min, conditions.resting_hr, conditions.mood_valence),
    moodTrend = mood_trend.orEmpty().map { it.valence },
    rail = rail.orEmpty().map { it.toModel() },
    gate = GateBlock(gate.best_split, gate.session_note, gate.splits.orEmpty()),
    strip = StripBlock(
        weekKm = strip.week_km,
        longRunKm = strip.long_run_km,
        z2Pct = strip.z2_pct?.roundToInt(),
        paceTrend = strip.pace_trend.orEmpty().map { it.roundToInt() },
    ),
    alti = AltiBlock(alti.vert_m, alti.goal_m, alti.load_kg, alti.carries),
)

fun ReportDTO.toModel() = Report(
    id = id,
    kind = kind,
    periodStart = period_start,
    periodEnd = period_end,
    bodyMd = body_md,
    headline = highlights?.get("headline") as? String,
    createdAt = created_at,
)

fun IntegrationStateDTO.toModel() = IntegrationState(
    connected = connected,
    lastSyncedAt = last_synced_at?.take(16)?.replace('T', ' '),
    athleteId = athlete_id,
)

fun IntegrationsStatusDTO.toModel() = IntegrationsStatus(
    strava = strava.toModel(),
    spotify = spotify.toModel(),
    calendar = calendar?.toModel(),
    github = github?.toModel(),
)

// ---- Chat (step 6) ----

data class ChatRequestDTO(val message: String)
data class ChatReplyDTO(val reply: String)
data class ChatMessageDTO(val id: Long, val role: String, val content: String, val created_at: String)

fun ChatMessageDTO.toModel() = ChatMessage(
    id = id,
    role = role,
    content = content,
    createdAt = created_at.take(16).replace('T', ' '),
)

// ---- Devices (step 7) ----

data class DeviceRegisterDTO(val token: String, val platform: String = "android")

// ---- Dashboard v2: AGENDA + QUOTE ----

data class UpcomingEventDTO(
    val start: String,
    val end: String,
    val subject: String?,
    val attendee_count: Int?,
    val is_recurring: Boolean,
)

data class CalendarEventDTO(
    val start: String,
    val end: String,
    val subject: String?,
    val busy_status: String,
    val attendee_count: Int?,
    val is_recurring: Boolean,
)

data class QuoteDTO(val day: String, val text: String, val source: String)

data class ReflectionDTO(val day: String, val text: String, val source: String)

data class MoodDTO(val day: String, val phrase: String, val source: String)

// ---- Dashboard v2: SIGNALS detail (behind the tappable COND/MoodTrace region) ----

data class SignalTrackDTO(
    val played_at: String,
    val track: String,
    val artist: String?,
    val valence: Double?,
    val energy: Double?,
)

data class SignalDayDTO(
    val day: String,
    val sleep_min: Int?,
    val sleep_score: Double?,
    val resting_hr: Int?,
    val mood_valence: Double?,
    val mood_energy: Double?,
)

data class GenreCountDTO(val genre: String, val count: Int)

// ---- GitHub contribution heatmap ----

data class DayContribDTO(val day: String, val count: Int)

data class GithubHeatmapDTO(
    val days: List<DayContribDTO>,
    val total: Int,
    val current_streak: Int,
    val longest_streak: Int,
    val source: String,
)

data class SignalsDTO(
    val recent_tracks: List<SignalTrackDTO>,
    val daily: List<SignalDayDTO>,
    val current_mood: String? = null,
    val genres: List<GenreCountDTO> = emptyList(),
)

// ---- Report detail: WEEK IN NUMBERS mini-charts (chat-graphs, step 5) ----

data class MetricDayDTO(
    val day: String,
    val km: Double,
    val vert_m: Double,
    val mood_valence: Double?,
    val sessions: Int,
)

data class ReportMetricsDTO(val days: List<MetricDayDTO>)
