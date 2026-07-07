package com.darius.crux.ui.theme

import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable

private val MeetSheetScheme = lightColorScheme(
    primary = GateRed,
    onPrimary = Chalk,
    secondary = Steel,
    onSecondary = Chalk,
    tertiary = Scree,
    onTertiary = Chalk,
    background = Chalk,
    onBackground = Ink,
    surface = Chalk,
    onSurface = Ink,
    surfaceVariant = ChalkShade,
    onSurfaceVariant = Graphite,
    outline = Hairline,
    error = GateRed,
)

@Composable
fun CruxTheme(content: @Composable () -> Unit) {
    // Light "meet sheet" only for now; inverted "night ops" variant is a later step.
    MaterialTheme(
        colorScheme = MeetSheetScheme,
        typography = CruxTypography,
        content = content,
    )
}
