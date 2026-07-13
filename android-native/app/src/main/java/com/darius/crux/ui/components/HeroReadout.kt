package com.darius.crux.ui.components

import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import com.darius.crux.ui.theme.Graphite
import com.darius.crux.ui.theme.Ink
import com.darius.crux.ui.theme.Space

/**
 * The hero readout — the one place Anton (displayLarge) is spent per screen: a big
 * engraved figure with a small mono unit and a caption above it, like the headline
 * number on an instrument face. Gives each screen a single focal point.
 */
@Composable
fun HeroReadout(
    value: String,
    unit: String,
    caption: String,
    modifier: Modifier = Modifier,
) {
    Column(modifier.fillMaxWidth().padding(horizontal = Space.screenH, vertical = Space.lg)) {
        Text(caption, style = MaterialTheme.typography.labelSmall.copy(color = Graphite))
        Spacer(Modifier.height(Space.xs))
        Row(verticalAlignment = Alignment.Bottom) {
            Text(value, style = MaterialTheme.typography.displayLarge)
            Spacer(Modifier.width(Space.sm))
            Text(
                unit,
                style = MaterialTheme.typography.titleSmall.copy(color = Ink),
                modifier = Modifier.padding(bottom = Space.md),
            )
        }
    }
}
