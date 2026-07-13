package com.darius.crux.ui.components

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.width
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import com.darius.crux.ui.theme.GateRed
import com.darius.crux.ui.theme.Graphite
import com.darius.crux.ui.theme.Space

/**
 * The one section header in the app: an engraved mono-caps label in [accent],
 * an optional graphite "▏subtitle", and an optional right-aligned [trailing]
 * action. Replaces the three ad-hoc header treatments that had drifted apart
 * (bare labelSmall caps, the instrument name+subtitle, and one-off titleSmall).
 */
@Composable
fun SectionHeader(
    label: String,
    modifier: Modifier = Modifier,
    subtitle: String? = null,
    accent: Color = GateRed,
    trailing: (@Composable () -> Unit)? = null,
) {
    Row(
        modifier = modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Text(label, style = MaterialTheme.typography.titleSmall.copy(color = accent))
            if (subtitle != null) {
                Spacer(Modifier.width(Space.md))
                Text("▏$subtitle", style = MaterialTheme.typography.titleSmall.copy(color = Graphite))
            }
        }
        if (trailing != null) trailing()
    }
}
