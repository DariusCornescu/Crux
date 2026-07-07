package com.darius.crux.ui.components

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.material3.MaterialTheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.text.AnnotatedString
import androidx.compose.ui.text.drawText
import androidx.compose.ui.text.rememberTextMeasurer
import androidx.compose.ui.unit.dp
import com.darius.crux.data.model.EffortMode
import com.darius.crux.data.model.RailEntry
import com.darius.crux.ui.theme.GateRed
import com.darius.crux.ui.theme.Hairline
import com.darius.crux.ui.theme.Ink
import com.darius.crux.ui.theme.Scree
import com.darius.crux.ui.theme.Steel
import java.util.Locale

private val DAYS = listOf("MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN")

/**
 * THE RAIL — the app's signature element. One baseline = the week's time axis.
 * Each effort mode renders in its own geometry on the same rail:
 *  explosive -> gate ticks cutting the rail (best split printed above)
 *  aerobic   -> steel bands lying along the rail (length = duration)
 *  loaded    -> olive relief rising off the rail (height = vert gain)
 */
@Composable
fun RailTape(rail: List<RailEntry>, modifier: Modifier = Modifier) {
    val tm = rememberTextMeasurer()
    val dayStyle = MaterialTheme.typography.labelSmall
    val splitStyle = MaterialTheme.typography.labelSmall.copy(color = GateRed)

    Canvas(modifier = modifier.fillMaxWidth().height(132.dp)) {
        val slot = size.width / 7f
        val railY = size.height * 0.58f

        // Baseline
        drawLine(Ink, Offset(0f, railY), Offset(size.width, railY), strokeWidth = 2.dp.toPx())

        // Day index ticks + labels
        DAYS.forEachIndexed { i, day ->
            drawLine(
                Hairline,
                Offset(slot * i, railY - 4.dp.toPx()),
                Offset(slot * i, railY + 4.dp.toPx()),
                strokeWidth = 1.dp.toPx(),
            )
            val layout = tm.measure(AnnotatedString(day), dayStyle)
            drawText(
                tm, day,
                topLeft = Offset(
                    slot * i + (slot - layout.size.width) / 2f,
                    size.height - layout.size.height.toFloat(),
                ),
                style = dayStyle,
            )
        }

        rail.forEach { entry ->
            val cx = slot * entry.dayIndex + slot / 2f
            when (entry.mode) {
                EffortMode.EXPLOSIVE -> {
                    // Gate tick: a timing beam cutting the rail
                    drawLine(
                        GateRed,
                        Offset(cx, railY - 34.dp.toPx()),
                        Offset(cx, railY + 12.dp.toPx()),
                        strokeWidth = 3.dp.toPx(),
                    )
                    entry.bestSplit?.let { split ->
                        val text = String.format(Locale.US, "%.2f", split)
                        val layout = tm.measure(AnnotatedString(text), splitStyle)
                        drawText(
                            tm, text,
                            topLeft = Offset(
                                cx - layout.size.width / 2f,
                                railY - 34.dp.toPx() - layout.size.height - 3.dp.toPx(),
                            ),
                            style = splitStyle,
                        )
                    }
                }

                EffortMode.AEROBIC -> {
                    // Band along the rail, length proportional to duration
                    val w = slot * (0.35f + 0.55f * (entry.durationS / 5400f).coerceAtMost(1f))
                    drawRect(
                        Steel,
                        topLeft = Offset(cx - w / 2f, railY - 4.dp.toPx()),
                        size = Size(w, 8.dp.toPx()),
                    )
                }

                EffortMode.LOADED -> {
                    // Relief rising off the rail, height proportional to vert gain
                    val frac = ((entry.vertM ?: 0.0).toFloat() / 600f).coerceAtMost(1f)
                    val h = 12.dp.toPx() + 34.dp.toPx() * frac
                    val w = slot * 0.62f
                    val relief = Path().apply {
                        moveTo(cx - w / 2f, railY)
                        lineTo(cx - w * 0.10f, railY - h)
                        lineTo(cx + w * 0.15f, railY - h * 0.55f)
                        lineTo(cx + w / 2f, railY)
                        close()
                    }
                    drawPath(relief, Scree)
                }
            }
        }
    }
}
