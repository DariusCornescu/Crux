package com.darius.splitrail.ui.screens

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.lifecycle.viewmodel.compose.viewModel
import com.darius.splitrail.data.model.Conditions
import com.darius.splitrail.data.model.DashboardData
import com.darius.splitrail.ui.components.AltiInstrument
import com.darius.splitrail.ui.components.ErrorStrip
import com.darius.splitrail.ui.components.GateInstrument
import com.darius.splitrail.ui.components.HairlineRule
import com.darius.splitrail.ui.components.LoadingStrip
import com.darius.splitrail.ui.components.MoodTrace
import com.darius.splitrail.ui.components.RailTape
import com.darius.splitrail.ui.components.StripInstrument
import com.darius.splitrail.ui.theme.GateRed
import com.darius.splitrail.ui.theme.Graphite
import com.darius.splitrail.ui.viewmodel.DashboardViewModel
import java.util.Locale

@Composable
fun DashboardScreen(viewModel: DashboardViewModel = viewModel()) {
    val uiState by viewModel.uiState.collectAsState()

    Column(modifier = Modifier.fillMaxSize().verticalScroll(rememberScrollState())) {
        BezelHeader(week = uiState.data?.week, isDemo = uiState.data?.isDemo == true)

        when {
            uiState.isLoading && uiState.data == null -> LoadingStrip()
            uiState.error != null && uiState.data == null ->
                ErrorStrip(uiState.error ?: "NO SIGNAL", onRetry = viewModel::load)
            uiState.data != null -> DashboardBody(uiState.data!!)
        }

        Spacer(Modifier.height(24.dp))
    }
}

@Composable
private fun DashboardBody(data: DashboardData) {
    ConditionsStrip(data.conditions)
    if (data.moodTrend.any { it != null }) {
        MoodTrace(data.moodTrend, Modifier.padding(horizontal = 20.dp))
        Spacer(Modifier.height(10.dp))
    }
    HairlineRule()

    // THE RAIL — signature element
    Column(Modifier.padding(horizontal = 20.dp, vertical = 14.dp)) {
        Text("THE RAIL — WK ${data.week}", style = MaterialTheme.typography.titleSmall)
        Spacer(Modifier.height(4.dp))
        RailTape(data.rail)
    }
    HairlineRule()

    GateInstrument(data.gate)
    HairlineRule()

    StripInstrument(data.strip)
    HairlineRule()

    AltiInstrument(data.alti)
}

@Composable
private fun BezelHeader(week: Int?, isDemo: Boolean) {
    Row(
        modifier = Modifier.fillMaxWidth().padding(horizontal = 20.dp, vertical = 14.dp),
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Text("SPLITRAIL", style = MaterialTheme.typography.titleSmall)
        Row(verticalAlignment = Alignment.CenterVertically) {
            if (isDemo) {
                Text(
                    "DEMO SIGNAL",
                    style = MaterialTheme.typography.labelSmall.copy(color = GateRed),
                )
                Spacer(Modifier.padding(horizontal = 6.dp))
            }
            Text(
                week?.let { "WK $it" } ?: "--",
                style = MaterialTheme.typography.labelMedium.copy(color = Graphite),
            )
        }
    }
}

@Composable
private fun ConditionsStrip(c: Conditions) {
    val sleep = c.sleepMin?.let { "${it / 60}:${String.format(Locale.US, "%02d", it % 60)}" } ?: "--"
    val rhr = c.restingHr?.toString() ?: "--"
    val mood = c.moodValence?.let { String.format(Locale.US, "▲%.2f", it) } ?: "--"

    Row(
        modifier = Modifier.fillMaxWidth().padding(horizontal = 20.dp).padding(bottom = 10.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Text("COND", style = MaterialTheme.typography.labelSmall.copy(color = GateRed))
        Spacer(Modifier.padding(horizontal = 6.dp))
        Text("SLEEP $sleep · RHR $rhr · MOOD $mood", style = MaterialTheme.typography.labelSmall)
    }
}
