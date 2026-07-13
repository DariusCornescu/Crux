package com.darius.crux.ui.components

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.darius.crux.network.UpcomingEventDTO
import com.darius.crux.ui.theme.GateRed
import com.darius.crux.ui.theme.Graphite
import com.darius.crux.ui.theme.Ink
import com.darius.crux.ui.theme.Space
import java.time.Duration
import java.time.LocalDate
import java.time.OffsetDateTime
import java.time.ZoneId
import java.time.ZonedDateTime
import java.time.format.DateTimeFormatter
import java.util.Locale

private val TIME_FMT: DateTimeFormatter = DateTimeFormatter.ofPattern("HH:mm", Locale.US)
private val WEEKDAY_FMT: DateTimeFormatter = DateTimeFormatter.ofPattern("EEE", Locale.US)
private val MONTH_FMT: DateTimeFormatter = DateTimeFormatter.ofPattern("MMM", Locale.US)

/**
 * NEXT UP — the next 1-2 work-calendar events, filling the slot the retired GATE
 * instrument used to occupy. Purely typographic, like a start list: no icons,
 * no cards. Tapping a row reveals a bit more detail underneath it.
 */
@Composable
fun AgendaBlock(
    events: List<UpcomingEventDTO>,
    expandedIndex: Int?,
    onToggle: (Int) -> Unit,
    modifier: Modifier = Modifier,
    onOpenAll: (() -> Unit)? = null,
) {
    val cb = onOpenAll
    val trailingAction: (@Composable () -> Unit)? = if (cb != null) { { AllAction(cb) } } else null
    Column(modifier = modifier.fillMaxWidth().padding(horizontal = Space.screenH, vertical = Space.sectionV)) {
        SectionHeader("NEXT UP", trailing = trailingAction)
        Spacer(Modifier.height(Space.md))

        events.forEachIndexed { index, event ->
            if (index != 0) Spacer(Modifier.height(Space.md))
            AgendaRow(event, expanded = expandedIndex == index, onToggle = { onToggle(index) })
        }
    }
}

@Composable
private fun AllAction(onClick: () -> Unit) {
    Text(
        "ALL →",
        style = MaterialTheme.typography.labelSmall.copy(color = GateRed),
        modifier = Modifier.clickable(onClick = onClick),
    )
}

/** One agenda row: `HH:mm–HH:mm · subject`. Defensive — malformed timestamps skip the row. */
@Composable
private fun AgendaRow(event: UpcomingEventDTO, expanded: Boolean, onToggle: () -> Unit) {
    val start = runCatching {
        OffsetDateTime.parse(event.start).atZoneSameInstant(ZoneId.systemDefault())
    }.getOrNull() ?: return
    val end = runCatching {
        OffsetDateTime.parse(event.end).atZoneSameInstant(ZoneId.systemDefault())
    }.getOrNull()

    val isToday = start.toLocalDate() == LocalDate.now(ZoneId.systemDefault())
    val timeColor = if (isToday) GateRed else Ink

    Column(Modifier.fillMaxWidth().clickable(onClick = onToggle)) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Text(
                "${start.format(TIME_FMT)}–${end?.format(TIME_FMT) ?: "--:--"}",
                style = MaterialTheme.typography.labelMedium.copy(color = timeColor),
            )
            Text(" · ", style = MaterialTheme.typography.labelMedium.copy(color = Graphite))
            Text(event.subject ?: "BUSY", style = MaterialTheme.typography.bodyMedium)
        }

        if (expanded) {
            AgendaDetail(event, start, end)
        }
    }
}

@Composable
private fun AgendaDetail(event: UpcomingEventDTO, start: ZonedDateTime, end: ZonedDateTime?) {
    Column(Modifier.padding(top = 6.dp, bottom = 2.dp)) {
        Text(event.subject ?: "BUSY", style = MaterialTheme.typography.bodyMedium)
        Spacer(Modifier.height(4.dp))
        Text(
            "${start.format(WEEKDAY_FMT).uppercase(Locale.US)} · " +
                "${start.format(MONTH_FMT).uppercase(Locale.US)} ${start.dayOfMonth}",
            style = MaterialTheme.typography.labelSmall.copy(color = Graphite),
        )
        end?.let {
            val minutes = Duration.between(start, it).toMinutes()
            Text("DURATION $minutes MIN", style = MaterialTheme.typography.labelSmall.copy(color = Graphite))
        }
        event.attendee_count?.let {
            Text("ATTENDEES $it", style = MaterialTheme.typography.labelSmall.copy(color = Graphite))
        }
    }
}
