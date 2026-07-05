package com.darius.splitrail.ui.screens

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.lifecycle.viewmodel.compose.viewModel
import com.darius.splitrail.ui.components.ErrorStrip
import com.darius.splitrail.ui.components.HairlineRule
import com.darius.splitrail.ui.components.LoadingStrip
import com.darius.splitrail.ui.theme.GateRed
import com.darius.splitrail.ui.theme.Graphite
import com.darius.splitrail.ui.theme.Ink
import com.darius.splitrail.ui.viewmodel.ReportDetailViewModel

@Composable
fun ReportDetailScreen(
    onBack: () -> Unit,
    viewModel: ReportDetailViewModel = viewModel(),
) {
    val uiState by viewModel.uiState.collectAsState()

    Column(Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(top = 18.dp)) {
        Row(Modifier.padding(horizontal = 20.dp)) {
            Text(
                "← REPORTS",
                style = MaterialTheme.typography.titleSmall.copy(color = Graphite),
                modifier = Modifier.clickable(onClick = onBack),
            )
        }
        Spacer(Modifier.height(12.dp))
        HairlineRule()

        when {
            uiState.isLoading -> LoadingStrip()
            uiState.error != null ->
                ErrorStrip(uiState.error ?: "NO SIGNAL", onRetry = viewModel::load)
            uiState.report != null -> {
                val report = uiState.report!!
                Column(Modifier.padding(horizontal = 20.dp, vertical = 14.dp)) {
                    Text(
                        "${report.kind.uppercase()} · ${report.periodStart} → ${report.periodEnd}",
                        style = MaterialTheme.typography.labelMedium.copy(color = Graphite),
                    )
                    Spacer(Modifier.height(12.dp))
                    MarkdownLite(report.bodyMd)
                }
            }
        }
        Spacer(Modifier.height(24.dp))
    }
}

/**
 * Deliberately small renderer for the report Markdown subset the backend
 * emits (#, ##, - bullets, plain paragraphs). A full Markdown dependency
 * isn't worth it for one screen.
 */
@Composable
private fun MarkdownLite(body: String) {
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
