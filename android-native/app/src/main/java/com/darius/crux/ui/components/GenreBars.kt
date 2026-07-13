package com.darius.crux.ui.components

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.darius.crux.network.GenreCountDTO
import com.darius.crux.ui.theme.Graphite
import com.darius.crux.ui.theme.Ink
import com.darius.crux.ui.theme.Space
import com.darius.crux.ui.theme.Steel

/**
 * GENRES — LAST 30: one horizontal bar per LLM-inferred sub-genre over the last
 * 30 listened tracks (count-desc from the backend). Plain filled Box bars, no
 * chart library — same idiom as ReportCharts. Empty list renders a single
 * "NO GENRES YET" line instead of an empty instrument.
 */
@Composable
fun GenreBars(genres: List<GenreCountDTO>, modifier: Modifier = Modifier) {
    Column(modifier.fillMaxWidth().padding(horizontal = Space.screenH, vertical = Space.sectionV)) {
        SectionHeader("GENRES — LAST 30")
        Spacer(Modifier.height(Space.md))
        if (genres.isEmpty()) {
            Text("NO GENRES YET", style = MaterialTheme.typography.labelSmall.copy(color = Graphite))
            return@Column
        }
        val max = genres.maxOf { it.count }.coerceAtLeast(1)
        genres.forEach { g ->
            Row(Modifier.fillMaxWidth().padding(vertical = 3.dp), verticalAlignment = Alignment.CenterVertically) {
                Text(
                    g.genre,
                    style = MaterialTheme.typography.bodyMedium.copy(color = Ink),
                    maxLines = 1,
                    modifier = Modifier.width(120.dp),
                )
                Box(Modifier.weight(1f).height(10.dp)) {
                    Box(Modifier.fillMaxWidth(g.count.toFloat() / max).fillMaxHeight().background(Steel))
                }
                Spacer(Modifier.width(8.dp))
                Text(
                    g.count.toString(),
                    style = MaterialTheme.typography.labelMedium.copy(color = Graphite),
                )
            }
        }
    }
}
