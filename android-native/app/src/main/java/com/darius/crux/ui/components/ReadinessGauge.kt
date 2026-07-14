package com.darius.crux.ui.components

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.width
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.darius.crux.network.ReadinessDTO
import com.darius.crux.ui.format.formatSleepHm
import com.darius.crux.ui.theme.ChalkShade
import com.darius.crux.ui.theme.GateRed
import com.darius.crux.ui.theme.Graphite
import com.darius.crux.ui.theme.Ink
import com.darius.crux.ui.theme.Scree
import com.darius.crux.ui.theme.Space
import com.darius.crux.ui.theme.Steel

/** Readiness: a word (READY/EASY/REST), the score, a band-colored bar, and drivers. */
@Composable
fun ReadinessGauge(r: ReadinessDTO, modifier: Modifier = Modifier) {
    val band = when (r.label) {
        "READY" -> Steel
        "EASY" -> Scree
        "REST" -> GateRed
        else -> Graphite
    }
    Column(modifier.fillMaxWidth()) {
        Row(verticalAlignment = Alignment.Bottom) {
            Text(r.label, style = MaterialTheme.typography.bodyLarge.copy(color = band))
            if (!r.low_data) {
                Spacer(Modifier.width(Space.sm))
                Text(r.score.toString(), style = MaterialTheme.typography.labelLarge.copy(color = Ink))
            }
        }
        Spacer(Modifier.height(Space.md))
        Box(Modifier.fillMaxWidth().height(10.dp).background(ChalkShade)) {
            Box(Modifier.fillMaxWidth(r.score.coerceIn(0, 100) / 100f).fillMaxHeight().background(band))
        }
        Spacer(Modifier.height(Space.sm))
        Text(driversLine(r), style = MaterialTheme.typography.labelSmall.copy(color = Graphite))
    }
}

private fun driversLine(r: ReadinessDTO): String {
    if (r.low_data) return "AWAITING SLEEP + RHR DATA"
    val sleep = r.sleep_min?.let { "SLEEP ${formatSleepHm(it)}" }
    val rhr = r.resting_hr?.let { "RHR $it" }
    val load = r.training_load?.let { "LOAD ${it.toInt()}" }
    return listOfNotNull(sleep, rhr, load).joinToString(" · ").ifEmpty { "—" }
}
