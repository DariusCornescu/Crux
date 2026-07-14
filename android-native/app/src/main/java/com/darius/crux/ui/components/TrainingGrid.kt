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
import com.darius.crux.network.TrainingDayDTO
import com.darius.crux.ui.theme.ChalkShade
import com.darius.crux.ui.theme.GateRed
import com.darius.crux.ui.theme.Scree
import com.darius.crux.ui.theme.Steel
import java.time.LocalDate

/**
 * Training contribution grid — the training counterpart of the CODE grid. Weeks as
 * columns, Mon..Sun rows, each square colored by the day's dominant mode (explosive
 * red / aerobic steel / loaded scree), intensity by volume. Same Canvas idiom.
 */
@Composable
fun TrainingGrid(days: List<TrainingDayDTO>, modifier: Modifier = Modifier) {
    if (days.isEmpty()) return
    val first = runCatching { LocalDate.parse(days.first().day) }.getOrNull()
    val offset = first?.let { (it.dayOfWeek.value + 6) % 7 } ?: 0   // Mon=0 .. Sun=6
    val cols = (days.size + offset + 6) / 7

    Canvas(modifier = modifier.fillMaxWidth().height(96.dp)) {
        val gap = 2.dp.toPx()
        val cellH = (size.height - 6 * gap) / 7f
        val cellW = if (cols > 0) (size.width - (cols - 1) * gap) / cols else size.width
        val cell = minOf(cellH, cellW)

        days.forEachIndexed { i, d ->
            val pos = i + offset
            drawRect(
                color = colorForMode(d.mode, d.minutes),
                topLeft = Offset((pos / 7) * (cell + gap), (pos % 7) * (cell + gap)),
                size = Size(cell, cell),
            )
        }
    }
}

private fun colorForMode(mode: String?, minutes: Int): Color {
    val base = when (mode) {
        "explosive" -> GateRed
        "aerobic" -> Steel
        "loaded" -> Scree
        else -> return ChalkShade
    }
    val alpha = when {
        minutes >= 90 -> 1f
        minutes >= 45 -> 0.80f
        minutes >= 20 -> 0.60f
        else -> 0.40f
    }
    return base.copy(alpha = alpha)
}
