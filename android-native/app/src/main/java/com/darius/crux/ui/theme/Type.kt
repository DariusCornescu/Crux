package com.darius.crux.ui.theme

import androidx.compose.material3.Typography
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.Font
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.sp
import com.darius.crux.R

/** Display — Anton. Used EXACTLY ONCE per screen: the hero readout. Never labels. */
val AntonFamily = FontFamily(Font(R.font.anton_regular))

/** Body — IBM Plex Sans. */
val PlexSans = FontFamily(
    Font(R.font.ibm_plex_sans_regular, FontWeight.Normal),
    Font(R.font.ibm_plex_sans_semibold, FontWeight.SemiBold),
)

/** Data/utility — IBM Plex Mono. Every number in the app renders in this. */
val PlexMono = FontFamily(
    Font(R.font.ibm_plex_mono_regular, FontWeight.Normal),
    Font(R.font.ibm_plex_mono_medium, FontWeight.Medium),
)

val CruxTypography = Typography(
    // Hero readout (the "6.98")
    displayLarge = TextStyle(
        fontFamily = AntonFamily,
        fontSize = 72.sp,
        letterSpacing = 0.sp,
        color = Ink,
    ),
    // Section prose
    bodyMedium = TextStyle(
        fontFamily = PlexSans,
        fontSize = 15.sp,
        lineHeight = 22.sp,
        color = Ink,
    ),
    bodySmall = TextStyle(
        fontFamily = PlexSans,
        fontSize = 13.sp,
        lineHeight = 18.sp,
        color = Graphite,
    ),
    // Engraved panel label: mono caps, letterspaced
    titleSmall = TextStyle(
        fontFamily = PlexMono,
        fontWeight = FontWeight.Medium,
        fontSize = 12.sp,
        letterSpacing = 2.sp,
        color = Ink,
    ),
    // Data readout rows
    labelLarge = TextStyle(
        fontFamily = PlexMono,
        fontWeight = FontWeight.Medium,
        fontSize = 15.sp,
        letterSpacing = 0.5.sp,
        color = Ink,
    ),
    labelMedium = TextStyle(
        fontFamily = PlexMono,
        fontSize = 13.sp,
        letterSpacing = 0.5.sp,
        color = Ink,
    ),
    labelSmall = TextStyle(
        fontFamily = PlexMono,
        fontSize = 11.sp,
        letterSpacing = 1.sp,
        color = Graphite,
        textAlign = TextAlign.Center,
    ),
)
