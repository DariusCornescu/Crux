package com.darius.crux.ui.screens

import androidx.compose.foundation.clickable
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
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.lifecycle.viewmodel.compose.viewModel
import com.darius.crux.data.model.Conditions
import com.darius.crux.data.model.DashboardData
import com.darius.crux.network.UpcomingEventDTO
import com.darius.crux.ui.components.AgendaBlock
import com.darius.crux.ui.components.AltiInstrument
import com.darius.crux.ui.components.ErrorStrip
import com.darius.crux.ui.components.HairlineRule
import com.darius.crux.ui.components.LoadingStrip
import com.darius.crux.ui.components.MoodTrace
import com.darius.crux.ui.components.RailTape
import com.darius.crux.ui.components.StripInstrument
import com.darius.crux.ui.theme.GateRed
import com.darius.crux.ui.theme.Graphite
import com.darius.crux.ui.viewmodel.DashboardViewModel
import java.util.Locale

@Composable
fun DashboardScreen(onOpenSignals: () -> Unit = {}, viewModel: DashboardViewModel = viewModel()) {
    val uiState by viewModel.uiState.collectAsState()
    val agenda by viewModel.agenda.collectAsState()
    val quote by viewModel.quote.collectAsState()
    var expandedAgendaIndex by remember { mutableStateOf<Int?>(null) }

    Column(modifier = Modifier.fillMaxSize().verticalScroll(rememberScrollState())) {
        BezelHeader(week = uiState.data?.week, isDemo = uiState.data?.isDemo == true)

        when {
            uiState.isLoading && uiState.data == null -> LoadingStrip()
            uiState.error != null && uiState.data == null ->
                ErrorStrip(uiState.error ?: "NO SIGNAL", onRetry = viewModel::load)
            uiState.data != null -> DashboardBody(
                data = uiState.data!!,
                agenda = agenda,
                expandedAgendaIndex = expandedAgendaIndex,
                onToggleAgenda = { index ->
                    expandedAgendaIndex = if (expandedAgendaIndex == index) null else index
                },
                quote = quote,
                onOpenSignals = onOpenSignals,
            )
        }

        Spacer(Modifier.height(24.dp))
    }
}

@Composable
private fun DashboardBody(
    data: DashboardData,
    agenda: List<UpcomingEventDTO>?,
    expandedAgendaIndex: Int?,
    onToggleAgenda: (Int) -> Unit,
    quote: String?,
    onOpenSignals: () -> Unit,
) {
    Column(Modifier.fillMaxWidth().clickable(onClick = onOpenSignals)) {
        ConditionsStrip(data.conditions)
        if (data.moodTrend.any { it != null }) {
            MoodTrace(data.moodTrend, Modifier.padding(horizontal = 20.dp))
            Spacer(Modifier.height(10.dp))
        }
    }
    HairlineRule()

    // THE RAIL — signature element
    Column(Modifier.padding(horizontal = 20.dp, vertical = 14.dp)) {
        Text("THE RAIL — WK ${data.week}", style = MaterialTheme.typography.titleSmall)
        Spacer(Modifier.height(4.dp))
        RailTape(data.rail)
    }
    HairlineRule()

    if (!agenda.isNullOrEmpty()) {
        AgendaBlock(agenda, expandedAgendaIndex, onToggleAgenda)
        HairlineRule()
    }

    StripInstrument(data.strip)
    HairlineRule()

    AltiInstrument(data.alti)

    if (quote != null) {
        HairlineRule()
        Text(
            quote,
            style = MaterialTheme.typography.bodyMedium.copy(
                color = Graphite,
                textAlign = TextAlign.Center,
            ),
            modifier = Modifier.fillMaxWidth().padding(horizontal = 20.dp, vertical = 12.dp),
        )
    }
}

@Composable
private fun BezelHeader(week: Int?, isDemo: Boolean) {
    Row(
        modifier = Modifier.fillMaxWidth().padding(horizontal = 20.dp, vertical = 14.dp),
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Text("CRUX", style = MaterialTheme.typography.titleSmall)
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
