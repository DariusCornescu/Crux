package com.darius.crux.ui.format

import java.util.Locale

/**
 * Shared formatters for the CONDITIONS metrics rendered on the dashboard COND
 * strip, the SIGNALS 14-day table and the readiness gauge — one source of truth
 * so those three surfaces never drift.
 */

/** Sleep minutes as "h:mm" (e.g. 432 -> "7:12"); null -> "--". */
fun formatSleepHm(minutes: Int?): String =
    minutes?.let { "${it / 60}:${String.format(Locale.US, "%02d", it % 60)}" } ?: "--"

/** Daily step total, compacted: 8241 -> "8.2K", small counts stay literal, null -> "--". */
fun formatSteps(steps: Int?): String = when {
    steps == null -> "--"
    steps >= 1000 -> String.format(Locale.US, "%.1fK", steps / 1000.0)
    else -> steps.toString()
}
