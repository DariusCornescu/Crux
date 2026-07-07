package com.darius.crux.ui.components

import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.width
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.darius.crux.ui.theme.GateRed
import com.darius.crux.ui.theme.Graphite
import com.darius.crux.ui.theme.Ink

/**
 * Deliberately small renderer for the Markdown subset the backend emits
 * (#, ##, - bullets, plain paragraphs). A full Markdown dependency isn't
 * worth it for two screens.
 */
@Composable
fun MarkdownLite(body: String) {
    Column {
        body.lines().forEach { raw ->
            val line = raw.trimEnd()
            when {
                line.startsWith("## ") -> {
                    Spacer(Modifier.height(14.dp))
                    Text(
                        line.removePrefix("## ").uppercase(),
                        style = MaterialTheme.typography.titleSmall.copy(color = GateRed),
                    )
                    Spacer(Modifier.height(4.dp))
                }
                line.startsWith("# ") -> {
                    Text(
                        line.removePrefix("# ").uppercase(),
                        style = MaterialTheme.typography.titleSmall.copy(color = Ink),
                    )
                    Spacer(Modifier.height(6.dp))
                }
                line.startsWith("- ") -> Row {
                    Text("—", style = MaterialTheme.typography.labelMedium.copy(color = Graphite))
                    Spacer(Modifier.width(8.dp))
                    Text(line.removePrefix("- "), style = MaterialTheme.typography.bodyMedium)
                }
                line.isBlank() -> Spacer(Modifier.height(6.dp))
                else -> Text(line, style = MaterialTheme.typography.bodyMedium)
            }
        }
    }
}
