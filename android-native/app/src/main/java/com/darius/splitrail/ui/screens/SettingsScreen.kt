package com.darius.splitrail.ui.screens

import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.darius.splitrail.ui.components.HairlineRule
import com.darius.splitrail.ui.components.InstrumentLabel
import com.darius.splitrail.ui.theme.Graphite
import com.darius.splitrail.ui.theme.Scree

@Composable
fun SettingsScreen() {
    Column(Modifier.fillMaxSize().padding(horizontal = 20.dp, vertical = 18.dp)) {
        InstrumentLabel("SETTINGS", "LINKS & ACCOUNTS", Scree)
        Spacer(Modifier.height(10.dp))
        HairlineRule()
        Spacer(Modifier.height(14.dp))
        listOf(
            "STRAVA" to "NOT CONNECTED",
            "SPOTIFY" to "NOT CONNECTED",
            "HEALTH CONNECT" to "LATER STEP",
        ).forEach { (name, status) ->
            Column(Modifier.fillMaxWidth().padding(vertical = 10.dp)) {
                Text(name, style = MaterialTheme.typography.labelLarge)
                Text(status, style = MaterialTheme.typography.labelSmall.copy(color = Graphite))
            }
            HairlineRule()
        }
    }
}
