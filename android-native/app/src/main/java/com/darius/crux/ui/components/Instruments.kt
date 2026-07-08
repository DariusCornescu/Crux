package com.darius.crux.ui.components

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.PathEffect
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.text.AnnotatedString
import androidx.compose.ui.text.drawText
import androidx.compose.ui.text.rememberTextMeasurer
import androidx.compose.ui.unit.dp
import com.darius.crux.data.model.AltiBlock
import com.darius.crux.data.model.StripBlock
import com.darius.crux.ui.theme.Graphite
import com.darius.crux.ui.theme.Hairline
import com.darius.crux.ui.theme.Ink
import com.darius.crux.ui.theme.Scree
import com.darius.crux.ui.theme.Steel
import java.util.Locale

/*
 * Two instruments, two geometries — deliberately NOT a shared card:
 *   STRIP is horizontal (continuous strip-chart trace)
 *   ALTI  is vertical   (ascending relief column vs. goal line)
 */

// ---------------------------------------------------------------- STRIP

@Composable
fun StripInstrument(strip: StripBlock, modifier: Modifier = Modifier) {
    Column(modifier = modifier.fillMaxWidth().padding(horizontal = 20.dp, vertical = 18.dp)) {
        InstrumentLabel("STRIP", "AEROBIC BASE", Steel)
        Spacer(Modifier.height(10.dp))

        if (strip.paceTrend.size >= 2) PaceStrip(strip.paceTrend)

        Spacer(Modifier.height(10.dp))
        Text(
            "WK ${String.format(Locale.US, "%.1f", strip.weekKm)} KM · " +
                "LONG ${String.format(Locale.US, "%.1f", strip.longRunKm)} KM" +
                (strip.z2Pct?.let { " · Z2 $it%" } ?: ""),
            style = MaterialTheme.typography.labelMedium,
        )
    }
}

/** Strip-chart recorder: per-km pace of the most recent run, drawn as a continuous trace. */
@Composable
private fun PaceStrip(paceTrend: List<Int>, modifier: Modifier = Modifier) {
    val tm = rememberTextMeasurer()
    val axisStyle = MaterialTheme.typography.labelSmall

    Canvas(modifier = modifier.fillMaxWidth().height(96.dp)) {
        val chartH = size.height - 16.dp.toPx()

        // Hairline grid — three horizontal rules like chart paper
        for (i in 0..2) {
            val y = chartH * i / 2f
            drawLine(Hairline, Offset(0f, y), Offset(size.width, y), 1.dp.toPx())
        }

        val minP = paceTrend.min().toFloat()
        val maxP = paceTrend.max().toFloat()
        val range = (maxP - minP).coerceAtLeast(1f)
        val stepX = size.width / (paceTrend.size - 1).toFloat()

        // Faster pace plots higher (it's a performance trace, not a price chart)
        fun yFor(p: Int) = chartH * (0.12f + 0.76f * (p - minP) / range)

        val trace = Path().apply {
            paceTrend.forEachIndexed { i, p ->
                if (i == 0) moveTo(0f, yFor(p)) else lineTo(stepX * i, yFor(p))
            }
        }
        drawPath(trace, Steel, style = Stroke(width = 2.dp.toPx()))

        // Endpoint marker + label with the last km's pace
        val lastY = yFor(paceTrend.last())
        drawLine(Steel, Offset(size.width - 6.dp.toPx(), lastY), Offset(size.width, lastY), 4.dp.toPx())

        val label = "${paceTrend.last() / 60}:${String.format(Locale.US, "%02d", paceTrend.last() % 60)}/KM"
        val layout = tm.measure(AnnotatedString(label), axisStyle)
        drawText(
            tm, label,
            topLeft = Offset(size.width - layout.size.width, size.height - layout.size.height.toFloat()),
            style = axisStyle,
        )
    }
}

// ---------------------------------------------------------------- ALTI

@Composable
fun AltiInstrument(alti: AltiBlock, modifier: Modifier = Modifier) {
    Column(modifier = modifier.fillMaxWidth().padding(horizontal = 20.dp, vertical = 18.dp)) {
        InstrumentLabel("ALTI", "UNDER LOAD", Scree)
        Spacer(Modifier.height(10.dp))

        AltiColumn(alti)

        Spacer(Modifier.height(10.dp))
        Text(
            "VERT ${alti.vertM.toInt()}/${alti.goalM.toInt()} M" +
                (alti.loadKg?.let { " · LOAD ${it.toInt()} KG" } ?: "") +
                " · ${alti.carries} CARRIES",
            style = MaterialTheme.typography.labelMedium,
        )
    }
}

/** Altimeter column: cumulative vert climbs toward the goal line. Vertical geometry, on purpose. */
@Composable
private fun AltiColumn(alti: AltiBlock, modifier: Modifier = Modifier) {
    val tm = rememberTextMeasurer()
    val axisStyle = MaterialTheme.typography.labelSmall

    Canvas(modifier = modifier.fillMaxWidth().height(140.dp)) {
        val baseY = size.height - 4.dp.toPx()
        val goalY = 14.dp.toPx()
        val plotLeft = size.width * 0.18f

        // Base + left axis
        drawLine(Ink, Offset(plotLeft, baseY), Offset(size.width, baseY), 2.dp.toPx())
        drawLine(Hairline, Offset(plotLeft, goalY), Offset(plotLeft, baseY), 1.dp.toPx())

        // Goal line — dashed, like an altimeter bug
        drawLine(
            Graphite, Offset(plotLeft, goalY), Offset(size.width, goalY), 1.dp.toPx(),
            pathEffect = PathEffect.dashPathEffect(floatArrayOf(8f, 8f)),
        )
        val goalLabel = "${alti.goalM.toInt()}"
        var layout = tm.measure(AnnotatedString(goalLabel), axisStyle)
        drawText(tm, goalLabel, topLeft = Offset(plotLeft - layout.size.width - 8.dp.toPx(), goalY - layout.size.height / 2f), style = axisStyle)

        // Cumulative relief: stepped ascent to current vert
        val frac = (alti.vertM / alti.goalM).toFloat().coerceIn(0f, 1f)
        val topY = baseY - (baseY - goalY) * frac
        val w = size.width - plotLeft
        val relief = Path().apply {
            moveTo(plotLeft, baseY)
            lineTo(plotLeft + w * 0.30f, baseY - (baseY - topY) * 0.45f)
            lineTo(plotLeft + w * 0.42f, baseY - (baseY - topY) * 0.38f)
            lineTo(plotLeft + w * 0.72f, topY)
            lineTo(plotLeft + w * 0.80f, topY)
            lineTo(plotLeft + w * 0.80f, baseY)
            close()
        }
        drawPath(relief, Scree)

        // Current-vert marker on the axis
        val vertLabel = "${alti.vertM.toInt()}"
        layout = tm.measure(AnnotatedString(vertLabel), axisStyle)
        drawText(tm, vertLabel, topLeft = Offset(plotLeft - layout.size.width - 8.dp.toPx(), topY - layout.size.height / 2f), style = axisStyle)
        drawLine(Ink, Offset(plotLeft - 4.dp.toPx(), topY), Offset(plotLeft + 4.dp.toPx(), topY), 2.dp.toPx())
    }
}
