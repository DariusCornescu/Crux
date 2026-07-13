package com.darius.crux.ui.components

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp
import com.darius.crux.network.DayContribDTO
import com.darius.crux.ui.theme.ChalkShade
import com.darius.crux.ui.theme.Steel
import java.time.LocalDate

/**
 * GitHub-style contribution grid — weeks as columns, Mon..Sun as rows, drawn as
 * small squares on a discrete Steel intensity ramp. Empty days are the paper's
 * inset shade. No rounded corners, no chart library — same Canvas idiom as MoodTrace.
 */
@Composable
fun ContributionGrid(days: List<DayContribDTO>, modifier: Modifier = Modifier) {
    if (days.isEmpty()) return
    val first = runCatching { LocalDate.parse(days.first().day) }.getOrNull()
    val offset = first?.let { (it.dayOfWeek.value + 6) % 7 } ?: 0   // Mon=0 .. Sun=6
    val cols = (days.size + offset + 6) / 7

    Canvas(modifier = modifier.fillMaxWidth().height(96.dp)) {
        val gap = 2.dp.toPx()
        val cellH = (size.height - 6 * gap) / 7f
        val cellW = if (cols > 0) (size.width - (cols - 1) * gap) / cols else size.width
        val cell = minOf(cellH, cellW)

        days.forEachIndexed { i, day ->
            val pos = i + offset
            val col = pos / 7
            val row = pos % 7
            drawRect(
                color = intensity(day.count),
                topLeft = Offset(col * (cell + gap), row * (cell + gap)),
                size = Size(cell, cell),
            )
        }
    }
}

private fun intensity(count: Int): Color = when {
    count <= 0 -> ChalkShade
    count <= 2 -> Steel.copy(alpha = 0.30f)
    count <= 5 -> Steel.copy(alpha = 0.55f)
    count <= 9 -> Steel.copy(alpha = 0.80f)
    else -> Steel
}
