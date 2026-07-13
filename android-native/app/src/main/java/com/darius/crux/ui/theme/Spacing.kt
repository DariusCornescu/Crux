package com.darius.crux.ui.theme

import androidx.compose.ui.unit.dp

/**
 * The one spacing scale for the app. Replaces the scattered magic dp values
 * (4/6/10/14/18/20/24) that had drifted across screens, so the timing-sheet
 * rhythm is consistent everywhere. Horizontal inset is a single token; vertical
 * rhythm steps through a small fixed set.
 */
object Space {
    /** Horizontal inset for every screen and section block. */
    val screenH = 20.dp

    val xs = 4.dp
    val sm = 6.dp
    val md = 10.dp
    val lg = 14.dp
    val xl = 18.dp
    val xxl = 24.dp

    /** Vertical padding inside a titled section block. */
    val sectionV = 18.dp

    /** Scaffold top padding, below the status bar. */
    val topInset = 18.dp
}
