package com.darius.crux.ui.screens

import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.lifecycle.viewmodel.compose.viewModel
import com.darius.crux.network.CalendarEventDTO
import com.darius.crux.ui.components.HairlineRule
import com.darius.crux.ui.components.LoadingStrip
import com.darius.crux.ui.components.ErrorStrip
import com.darius.crux.ui.components.MeetSheetScreen
import com.darius.crux.ui.components.SectionHeader
import com.darius.crux.ui.theme.GateRed
import com.darius.crux.ui.theme.Graphite
import com.darius.crux.ui.theme.Ink
import com.darius.crux.ui.theme.Space
import com.darius.crux.ui.viewmodel.MeetingsViewModel
import java.time.LocalDate
import java.time.OffsetDateTime
import java.time.ZoneId
import java.time.format.DateTimeFormatter
import java.util.Locale

private val TIME_FMT: DateTimeFormatter = DateTimeFormatter.ofPattern("HH:mm", Locale.US)
private val DAY_FMT: DateTimeFormatter = DateTimeFormatter.ofPattern("EEE · MMM d", Locale.US)

/**
 * MEETINGS — the full calls record. UPCOMING pinned at the top (soonest first,
 * today in GateRed), then PAST grouped by day, most-recent first. Reached by
 * tapping the NEXT UP block on the Dashboard.
 */
@Composable
fun MeetingsScreen(
    onBack: () -> Unit,
    viewModel: MeetingsViewModel = viewModel(),
) {
    val uiState by viewModel.uiState.collectAsState()

    MeetSheetScreen(title = "MEETINGS", onBack = onBack) {
        when {
            uiState.isLoading && uiState.upcoming.isEmpty() && uiState.past.isEmpty() -> LoadingStrip()
            uiState.error != null && uiState.upcoming.isEmpty() && uiState.past.isEmpty() ->
                ErrorStrip(uiState.error ?: "NO SIGNAL", onRetry = viewModel::load)
            else -> {
                Column(Modifier.fillMaxWidth().padding(horizontal = Space.screenH, vertical = Space.sectionV)) {
                    SectionHeader("UPCOMING")
                    Spacer(Modifier.height(Space.md))
                    if (uiState.upcoming.isEmpty()) {
                        Text("NOTHING SCHEDULED", style = MaterialTheme.typography.labelSmall.copy(color = Graphite))
                    } else {
                        EventList(uiState.upcoming)
                    }
                }
                HairlineRule()
                Column(Modifier.fillMaxWidth().padding(horizontal = Space.screenH, vertical = Space.sectionV)) {
                    SectionHeader("PAST")
                    Spacer(Modifier.height(Space.md))
                    if (uiState.past.isEmpty()) {
                        Text("NO HISTORY YET", style = MaterialTheme.typography.labelSmall.copy(color = Graphite))
                    } else {
                        EventList(uiState.past)
                    }
                }
            }
        }
        Spacer(Modifier.height(Space.xxl))
    }
}

/** Day-grouped meeting rows: a weekday header, then `HH:mm–HH:mm · subject` per row. */
@Composable
private fun EventList(events: List<CalendarEventDTO>) {
    val zone = ZoneId.systemDefault()
    val today = LocalDate.now(zone)
    var lastDay: LocalDate? = null

    events.forEach { e ->
        val start = runCatching { OffsetDateTime.parse(e.start).atZoneSameInstant(zone) }.getOrNull()
            ?: return@forEach
        val end = runCatching { OffsetDateTime.parse(e.end).atZoneSameInstant(zone) }.getOrNull()
        val day = start.toLocalDate()

        if (day != lastDay) {
            if (lastDay != null) Spacer(Modifier.height(Space.md))
            Text(
                start.format(DAY_FMT).uppercase(Locale.US),
                style = MaterialTheme.typography.labelSmall.copy(color = Graphite),
            )
            Spacer(Modifier.height(Space.sm))
            lastDay = day
        }

        val timeColor = if (day == today) GateRed else Ink
        Row(Modifier.fillMaxWidth()) {
            Text(
                "${start.format(TIME_FMT)}–${end?.format(TIME_FMT) ?: "--:--"}",
                style = MaterialTheme.typography.labelMedium.copy(color = timeColor),
            )
            Text(" · ", style = MaterialTheme.typography.labelMedium.copy(color = Graphite))
            Text(
                e.subject ?: "BUSY",
                style = MaterialTheme.typography.bodyMedium.copy(color = Ink),
                modifier = Modifier.weight(1f),
            )
        }
        Spacer(Modifier.height(Space.sm))
    }
}
