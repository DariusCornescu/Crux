package com.darius.crux.ui.components

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp
import com.darius.crux.ui.theme.GateRed
import com.darius.crux.ui.theme.Graphite
import com.darius.crux.ui.theme.Hairline

/** 1dp rule — the only divider in the app, like a printed timing sheet. */
@Composable
fun HairlineRule(modifier: Modifier = Modifier) {
    Box(modifier.fillMaxWidth().height(1.dp).background(Hairline))
}

/**
 * Engraved panel label: colored instrument name + graphite subtitle. Kept as a
 * thin alias over [SectionHeader] so there is a single header implementation.
 */
@Composable
fun InstrumentLabel(name: String, subtitle: String, color: Color) {
    SectionHeader(label = name, subtitle = subtitle, accent = color)
}

/** Loading state, instrument-style — no spinners on a timing sheet. */
@Composable
fun LoadingStrip(label: String = "ACQUIRING SIGNAL…") {
    Column(Modifier.fillMaxWidth().padding(vertical = 24.dp)) {
        HairlineRule()
        Text(
            label,
            style = MaterialTheme.typography.labelSmall.copy(color = Graphite),
            modifier = Modifier.padding(horizontal = 20.dp, vertical = 12.dp),
        )
        HairlineRule()
    }
}

/** Empty state — hairline-bracketed line, matching [LoadingStrip] exactly. */
@Composable
fun EmptyStrip(label: String) {
    Column(Modifier.fillMaxWidth().padding(vertical = 24.dp)) {
        HairlineRule()
        Text(
            label,
            style = MaterialTheme.typography.labelSmall.copy(color = Graphite),
            modifier = Modifier.padding(horizontal = 20.dp, vertical = 12.dp),
        )
        HairlineRule()
    }
}

/** Error state with a retry affordance. */
@Composable
fun ErrorStrip(message: String, onRetry: () -> Unit) {
    Column(Modifier.fillMaxWidth().padding(vertical = 24.dp)) {
        HairlineRule()
        Column(Modifier.padding(horizontal = 20.dp, vertical = 12.dp)) {
            Text(message, style = MaterialTheme.typography.labelSmall.copy(color = GateRed))
            Spacer(Modifier.height(8.dp))
            Text(
                "RETRY",
                style = MaterialTheme.typography.titleSmall.copy(color = GateRed),
                modifier = Modifier.clickable(onClick = onRetry).padding(vertical = 4.dp),
            )
        }
        HairlineRule()
    }
}
