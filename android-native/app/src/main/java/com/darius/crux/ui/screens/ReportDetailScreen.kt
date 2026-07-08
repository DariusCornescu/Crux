package com.darius.crux.ui.screens

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
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
import com.darius.crux.ui.components.ErrorStrip
import com.darius.crux.ui.components.HairlineRule
import com.darius.crux.ui.components.LoadingStrip
import com.darius.crux.ui.components.MarkdownLite
import com.darius.crux.ui.components.WeekInNumbers
import com.darius.crux.ui.theme.Graphite
import com.darius.crux.ui.viewmodel.ReportDetailViewModel

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
                }

                uiState.metrics?.let { metrics ->
                    WeekInNumbers(metrics)
                    HairlineRule()
                }

                Column(Modifier.padding(horizontal = 20.dp, vertical = 14.dp)) {
                    MarkdownLite(report.bodyMd)
                }
            }
        }
        Spacer(Modifier.height(24.dp))
    }
}
