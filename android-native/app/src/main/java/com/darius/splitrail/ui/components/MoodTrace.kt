package com.darius.splitrail.ui.components

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.unit.dp
import com.darius.splitrail.ui.theme.Graphite
import com.darius.splitrail.ui.theme.Hairline
import com.darius.splitrail.ui.theme.Ink

/**
 * 14-day mood proxy from Spotify listening valence — a barograph strip.
 * Mood is context, not a training mode, so it stays neutral ink and small;
 * days without listening data render as hairline stubs, not zeros.
 */
@Composable
fun MoodTrace(moodTrend: List<Double?>, modifier: Modifier = Modifier) {
    Canvas(modifier = modifier.fillMaxWidth().height(36.dp)) {
        if (moodTrend.isEmpty()) return@Canvas
        val baseY = size.height - 2.dp.toPx()
        val slot = size.width / moodTrend.size
        val barW = (slot * 0.45f).coerceAtMost(6.dp.toPx())
        val maxH = size.height - 8.dp.toPx()

        drawLine(Hairline, Offset(0f, baseY), Offset(size.width, baseY), 1.dp.toPx())

        moodTrend.forEachIndexed { i, valence ->
            val cx = slot * i + slot / 2f
            if (valence == null) {
                // no listening data — a stub tick, visually distinct from a low mood
                drawLine(Graphite, Offset(cx, baseY - 2.dp.toPx()), Offset(cx, baseY), 1.dp.toPx())
            } else {
                val h = (maxH * valence.toFloat().coerceIn(0f, 1f)).coerceAtLeast(2.dp.toPx())
                drawRect(
                    Ink,
                    topLeft = Offset(cx - barW / 2f, baseY - h),
                    size = Size(barW, h),
                )
            }
        }
    }
}
