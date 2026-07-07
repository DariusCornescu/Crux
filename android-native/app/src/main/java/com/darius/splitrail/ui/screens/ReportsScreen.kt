package com.darius.splitrail.ui.screens

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.lifecycle.viewmodel.compose.viewModel
import com.darius.splitrail.data.model.Report
import com.darius.splitrail.ui.components.ErrorStrip
import com.darius.splitrail.ui.components.HairlineRule
import com.darius.splitrail.ui.components.InstrumentLabel
import com.darius.splitrail.ui.components.LoadingStrip
import com.darius.splitrail.ui.theme.GateRed
import com.darius.splitrail.ui.theme.Graphite
import com.darius.splitrail.ui.viewmodel.ReportsViewModel

@Composable
fun ReportsScreen(
    onOpenReport: (Long) -> Unit,
    viewModel: ReportsViewModel = viewModel(),
) {
    val uiState by viewModel.uiState.collectAsState()

    Column(Modifier.fillMaxSize().padding(top = 18.dp)) {
        Row(
            modifier = Modifier.fillMaxWidth().padding(horizontal = 20.dp),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically,
        ) {
            InstrumentLabel("REPORTS", "WEEKLY ANALYSIS", GateRed)
            Text(
                if (uiState.isGenerating) "GENERATING…" else "GENERATE",
                style = MaterialTheme.typography.titleSmall.copy(
                    color = if (uiState.isGenerating) Graphite else GateRed),
                modifier = Modifier.clickable(enabled = !uiState.isGenerating) { viewModel.generate() },
            )
        }
        Spacer(Modifier.height(10.dp))
        HairlineRule()

        when {
            uiState.isLoading -> LoadingStrip()
            uiState.error != null && uiState.reports.isEmpty() ->
                ErrorStrip(uiState.error ?: "NO SIGNAL", onRetry = viewModel::load)
            uiState.reports.isEmpty() -> Text(
                "No reports yet. GENERATE builds one for the last completed week; " +
                    "the backend also runs every Monday 05:00 UTC.",
                style = MaterialTheme.typography.bodySmall,
                modifier = Modifier.padding(20.dp),
            )
            else -> LazyColumn {
                items(uiState.reports, key = { it.id }) { report ->
                    ReportRow(report, onClick = { onOpenReport(report.id) })
                    HairlineRule()
                }
            }
        }
    }
}

@Composable
private fun ReportRow(report: Report, onClick: () -> Unit) {
    Column(
        Modifier.fillMaxWidth().clickable(onClick = onClick)
            .padding(horizontal = 20.dp, vertical = 14.dp),
    ) {
        Text(
            "${report.kind.uppercase()} · ${report.periodStart} → ${report.periodEnd}",
            style = MaterialTheme.typography.labelMedium,
        )
        report.headline?.let {
            Spacer(Modifier.height(4.dp))
            Text(it, style = MaterialTheme.typography.bodySmall)
        }
    }
}
