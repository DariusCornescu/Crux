package com.darius.crux.ui.screens

import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.lifecycle.viewmodel.compose.viewModel
import com.darius.crux.network.SignalDayDTO
import com.darius.crux.network.SignalTrackDTO
import com.darius.crux.ui.components.ErrorStrip
import com.darius.crux.ui.components.GenreBars
import com.darius.crux.ui.components.HairlineRule
import com.darius.crux.ui.components.LoadingStrip
import com.darius.crux.ui.components.MeetSheetScreen
import com.darius.crux.ui.components.SectionHeader
import com.darius.crux.ui.theme.Graphite
import com.darius.crux.ui.theme.Ink
import com.darius.crux.ui.theme.Space
import com.darius.crux.ui.viewmodel.SignalsViewModel
import java.time.LocalDate
import java.time.OffsetDateTime
import java.time.ZoneId
import java.time.ZonedDateTime
import java.time.format.DateTimeFormatter
import java.util.Locale

private val TIME_FMT: DateTimeFormatter = DateTimeFormatter.ofPattern("HH:mm", Locale.US)
private val WEEKDAY_FMT: DateTimeFormatter = DateTimeFormatter.ofPattern("EEE", Locale.US)
private val MONTH_FMT: DateTimeFormatter = DateTimeFormatter.ofPattern("MMM", Locale.US)
private val DAY_ROW_FMT: DateTimeFormatter = DateTimeFormatter.ofPattern("EEE MM/dd", Locale.US)

/**
 * SIGNALS — the detail screen behind the tappable COND/MoodTrace region on the
 * Dashboard: last 30 tracks listened to (grouped by day) and 14 days of sleep/
 * RHR/mood conditions. Timing-sheet layout, no cards.
 */
@Composable
fun SignalsScreen(
    onBack: () -> Unit,
    viewModel: SignalsViewModel = viewModel(),
) {
    val uiState by viewModel.uiState.collectAsState()

    MeetSheetScreen(title = "SIGNALS", onBack = onBack) {
        when {
            uiState.isLoading -> LoadingStrip()
            uiState.error != null ->
                ErrorStrip(uiState.error ?: "NO SIGNAL", onRetry = viewModel::load)
            uiState.data != null -> {
                val data = uiState.data!!
                data.current_mood?.let { phrase ->
                    Column(Modifier.fillMaxWidth().padding(horizontal = Space.screenH, vertical = Space.sectionV)) {
                        SectionHeader("MOOD")
                        Spacer(Modifier.height(Space.sm))
                        Text(phrase, style = MaterialTheme.typography.titleSmall.copy(color = Ink))
                    }
                    HairlineRule()
                }
                ListeningSection(data.recent_tracks)
                if (data.genres.isNotEmpty()) {
                    HairlineRule()
                    GenreBars(data.genres)
                }
                HairlineRule()
                ConditionsSection(data.daily)
            }
        }
        Spacer(Modifier.height(Space.xxl))
    }
}

/** LISTENING — LAST 30: tracks grouped by day, newest-first (order comes from the backend). */
@Composable
private fun ListeningSection(tracks: List<SignalTrackDTO>) {
    // Defensive parse — malformed timestamps are dropped rather than crashing the row.
    val parsed = tracks.mapNotNull { track ->
        runCatching {
            OffsetDateTime.parse(track.played_at).atZoneSameInstant(ZoneId.systemDefault())
        }.getOrNull()?.let { track to it }
    }

    Column(Modifier.fillMaxWidth().padding(horizontal = Space.screenH, vertical = Space.sectionV)) {
        SectionHeader("LISTENING — LAST 30")
        Spacer(Modifier.height(Space.md))

        if (parsed.isEmpty()) {
            Text("NO SIGNAL YET", style = MaterialTheme.typography.labelSmall.copy(color = Graphite))
        } else {
            var lastDay: LocalDate? = null
            parsed.forEach { (track, time) ->
                val day = time.toLocalDate()
                if (day != lastDay) {
                    if (lastDay != null) Spacer(Modifier.height(Space.md))
                    Text(
                        "${time.format(WEEKDAY_FMT).uppercase(Locale.US)} · " +
                            "${time.format(MONTH_FMT).uppercase(Locale.US)} ${time.dayOfMonth}",
                        style = MaterialTheme.typography.labelSmall.copy(color = Graphite),
                    )
                    Spacer(Modifier.height(Space.sm))
                    lastDay = day
                }
                TrackRow(track, time)
                Spacer(Modifier.height(Space.sm))
            }
        }
    }
}

@Composable
private fun TrackRow(track: SignalTrackDTO, time: ZonedDateTime) {
    val titleArtist = track.artist?.let { "${track.track} — $it" } ?: track.track
    val valence = track.valence?.let { String.format(Locale.US, "▲%.2f", it) } ?: "--"

    Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
        Text(time.format(TIME_FMT), style = MaterialTheme.typography.labelMedium.copy(color = Graphite))
        Spacer(Modifier.width(Space.md))
        Text(
            titleArtist,
            style = MaterialTheme.typography.bodyMedium.copy(color = Ink),
            modifier = Modifier.weight(1f),
        )
        Text(valence, style = MaterialTheme.typography.labelMedium.copy(color = Ink))
    }
}

/** CONDITIONS — 14 DAYS: header row + one row per day, kept even when the listening section is empty. */
@Composable
private fun ConditionsSection(days: List<SignalDayDTO>) {
    Column(Modifier.fillMaxWidth().padding(horizontal = Space.screenH, vertical = Space.sectionV)) {
        SectionHeader("CONDITIONS — 14 DAYS")
        Spacer(Modifier.height(Space.md))

        Row(Modifier.fillMaxWidth()) {
            Text("DAY", style = MaterialTheme.typography.labelSmall.copy(color = Graphite), modifier = Modifier.weight(1f))
            Text("SLEEP", style = MaterialTheme.typography.labelSmall.copy(color = Graphite), modifier = Modifier.weight(1f))
            Text("RHR", style = MaterialTheme.typography.labelSmall.copy(color = Graphite), modifier = Modifier.weight(1f))
        }
        Spacer(Modifier.height(Space.sm))

        days.forEach { day ->
            DayRow(day)
        }
    }
}

@Composable
private fun DayRow(day: SignalDayDTO) {
    val label = runCatching { LocalDate.parse(day.day).format(DAY_ROW_FMT).uppercase(Locale.US) }
        .getOrDefault(day.day)
    val sleep = day.sleep_min?.let { "${it / 60}:${String.format(Locale.US, "%02d", it % 60)}" } ?: "--"
    val rhr = day.resting_hr?.toString() ?: "--"

    Row(Modifier.fillMaxWidth().padding(vertical = Space.xs)) {
        Text(label, style = MaterialTheme.typography.labelMedium.copy(color = Ink), modifier = Modifier.weight(1f))
        Text(sleep, style = MaterialTheme.typography.labelMedium.copy(color = Ink), modifier = Modifier.weight(1f))
        Text(rhr, style = MaterialTheme.typography.labelMedium.copy(color = Ink), modifier = Modifier.weight(1f))
    }
}
