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
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.darius.splitrail.data.model.Conditions
import com.darius.splitrail.data.model.DashboardData
import com.darius.splitrail.data.sampleDashboard
import com.darius.splitrail.ui.components.AltiInstrument
import com.darius.splitrail.ui.components.GateInstrument
import com.darius.splitrail.ui.components.HairlineRule
import com.darius.splitrail.ui.components.RailTape
import com.darius.splitrail.ui.components.StripInstrument
import com.darius.splitrail.ui.theme.GateRed
import com.darius.splitrail.ui.theme.Graphite
import java.util.Locale

/** Renders sampleDashboard until the API client lands (build step 3). */
@Composable
fun DashboardScreen(data: DashboardData = sampleDashboard) {
    Column(modifier = Modifier.fillMaxSize().verticalScroll(rememberScrollState())) {
        BezelHeader(week = data.week)
        ConditionsStrip(data.conditions)
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

        Spacer(Modifier.height(24.dp))
    }
}

@Composable
private fun BezelHeader(week: Int) {
    Row(
        modifier = Modifier.fillMaxWidth().padding(horizontal = 20.dp, vertical = 14.dp),
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Text("SPLITRAIL", style = MaterialTheme.typography.titleSmall)
        Text("WK $week", style = MaterialTheme.typography.labelMedium.copy(color = Graphite))
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
