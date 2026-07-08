package com.darius.crux.ui.components

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp
import com.darius.crux.network.MetricDayDTO
import com.darius.crux.ui.theme.GateRed
import com.darius.crux.ui.theme.Graphite
import com.darius.crux.ui.theme.Hairline
import com.darius.crux.ui.theme.Ink
import com.darius.crux.ui.theme.Scree
import com.darius.crux.ui.theme.Steel
import java.util.Locale

/**
 * WEEK IN NUMBERS — three per-day mini-instruments on the report detail screen:
 * distance (km), vert gain (m), mood (Spotify valence proxy). Plain Canvas bars
 * / polyline, no chart library — same idiom as MoodTrace/RailTape.
 */
@Composable
fun WeekInNumbers(days: List<MetricDayDTO>, modifier: Modifier = Modifier) {
    Column(modifier = modifier.fillMaxWidth().padding(horizontal = 20.dp, vertical = 18.dp)) {
        Text("WEEK IN NUMBERS", style = MaterialTheme.typography.labelSmall.copy(color = GateRed))
        Spacer(Modifier.height(12.dp))

        val maxKm = days.maxOfOrNull { it.km } ?: 0.0
        BarChart(
            caption = "KM",
            maxLabel = "MAX ${String.format(Locale.US, "%.1f", maxKm)}",
            values = days.map { it.km },
            color = Steel,
        )
        Spacer(Modifier.height(14.dp))

        val maxVert = days.maxOfOrNull { it.vert_m } ?: 0.0
        BarChart(
            caption = "VERT",
            maxLabel = "MAX ${String.format(Locale.US, "%.0f", maxVert)}",
            values = days.map { it.vert_m },
            color = Scree,
        )
        Spacer(Modifier.height(14.dp))

        val maxMood = days.mapNotNull { it.mood_valence }.maxOrNull()
        MoodChart(
            maxLabel = maxMood?.let { "MAX ${String.format(Locale.US, "▲%.2f", it)}" } ?: "MAX --",
            values = days.map { it.mood_valence },
        )
    }
}

@Composable
private fun ChartCaption(caption: String, maxLabel: String) {
    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
        Text(caption, style = MaterialTheme.typography.labelSmall.copy(color = Graphite))
        Text(maxLabel, style = MaterialTheme.typography.labelMedium.copy(color = Ink))
    }
}

/**
 * One bar per day, equal slots, height proportional to value/max. A zero (or
 * negative, defensively) day renders no bar; an all-zero week still renders the
 * caption + baseline with an empty plot area — never crashes on a flat week.
 */
@Composable
private fun BarChart(caption: String, maxLabel: String, values: List<Double>, color: Color) {
    ChartCaption(caption, maxLabel)
    Spacer(Modifier.height(4.dp))
    val maxV = values.maxOrNull()?.takeIf { it > 0.0 } ?: 0.0
    Canvas(modifier = Modifier.fillMaxWidth().height(48.dp)) {
        if (values.isEmpty()) return@Canvas
        val baseY = size.height - 2.dp.toPx()
        drawLine(Hairline, Offset(0f, baseY), Offset(size.width, baseY), 1.dp.toPx())
        if (maxV <= 0.0) return@Canvas

        val slot = size.width / values.size
        val barW = slot * 0.6f
        val maxH = size.height - 4.dp.toPx()

        values.forEachIndexed { i, v ->
            if (v <= 0.0) return@forEachIndexed
            val cx = slot * i + slot / 2f
            val h = (maxH * (v / maxV).toFloat()).coerceAtLeast(2.dp.toPx())
            drawRect(
                color,
                topLeft = Offset(cx - barW / 2f, baseY - h),
                size = Size(barW, h),
            )
        }
    }
}

/**
 * Polyline through non-null mood valence points (y: 0..1, inverted so higher
 * valence draws higher). Null days break the line — only adjacent non-null
 * days get a connecting segment, mirroring MoodTrace's treatment of gaps.
 */
@Composable
private fun MoodChart(maxLabel: String, values: List<Double?>) {
    ChartCaption("MOOD", maxLabel)
    Spacer(Modifier.height(4.dp))
    Canvas(modifier = Modifier.fillMaxWidth().height(48.dp)) {
        if (values.isEmpty()) return@Canvas
        val baseY = size.height - 2.dp.toPx()
        drawLine(Hairline, Offset(0f, baseY), Offset(size.width, baseY), 1.dp.toPx())

        val slot = size.width / values.size
        val topY = 2.dp.toPx()
        val plotH = size.height - 4.dp.toPx()

        fun pointFor(i: Int, valence: Double): Offset {
            val cx = slot * i + slot / 2f
            val cy = topY + plotH * (1f - valence.toFloat().coerceIn(0f, 1f))
            return Offset(cx, cy)
        }

        var prevPoint: Offset? = null
        var prevIndex = -1
        values.forEachIndexed { i, valence ->
            if (valence == null) {
                prevPoint = null
                prevIndex = -1
                return@forEachIndexed
            }
            val point = pointFor(i, valence)
            if (prevPoint != null && prevIndex == i - 1) {
                drawLine(Ink, prevPoint!!, point, strokeWidth = 2.dp.toPx())
            }
            drawCircle(Ink, radius = 1.5.dp.toPx(), center = point)
            prevPoint = point
            prevIndex = i
        }
    }
}
