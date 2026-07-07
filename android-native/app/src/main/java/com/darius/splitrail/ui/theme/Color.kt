package com.darius.splitrail.ui.theme

import androidx.compose.ui.graphics.Color

// ---- MEET SHEET palette — the only six colors in the app ----

/** Background — warm paper, like a meet timing sheet / topo map. */
val Chalk = Color(0xFFEFEAE0)

/** Text, instrument frames, hairline rules. */
val Ink = Color(0xFF16181D)

/** Secondary text, axis labels. */
val Graphite = Color(0xFF565A63)

/** Explosive / anaerobic — timing-beam red. Also alerts & PB marks. */
val GateRed = Color(0xFFC33B2A)

/** Aerobic — drafting-blue for continuous traces. */
val Steel = Color(0xFF2F5D7C)

/** Loaded — field-olive for ruck/hike relief. */
val Scree = Color(0xFF6B6349)

// Derived, not new tokens:
val Hairline = Ink.copy(alpha = 0.22f)
val ChalkShade = Color(0xFFE5DFD2) // pressed/inset areas
