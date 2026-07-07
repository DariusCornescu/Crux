package com.darius.crux.ui.screens

import android.content.Intent
import android.net.Uri
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import androidx.lifecycle.viewmodel.compose.viewModel
import com.darius.crux.data.model.IntegrationState
import com.darius.crux.ui.components.HairlineRule
import com.darius.crux.ui.components.InstrumentLabel
import com.darius.crux.ui.components.LoadingStrip
import com.darius.crux.ui.theme.GateRed
import com.darius.crux.ui.theme.Graphite
import com.darius.crux.ui.theme.Scree
import com.darius.crux.ui.theme.Steel
import com.darius.crux.ui.viewmodel.SettingsViewModel

@Composable
fun SettingsScreen(viewModel: SettingsViewModel = viewModel()) {
    val uiState by viewModel.uiState.collectAsState()
    val context = LocalContext.current
    val openUrl: (String) -> Unit = { url ->
        context.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(url)))
    }

    Column(Modifier.fillMaxSize().padding(top = 18.dp)) {
        Row(
            modifier = Modifier.fillMaxWidth().padding(horizontal = 20.dp),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically,
        ) {
            InstrumentLabel("SETTINGS", "LINKS & ACCOUNTS", Scree)
            Text(
                "REFRESH",
                style = MaterialTheme.typography.titleSmall.copy(color = Graphite),
                modifier = Modifier.clickable { viewModel.refresh() },
            )
        }
        Spacer(Modifier.height(10.dp))
        HairlineRule()

        if (uiState.isLoading && uiState.status == null) {
            LoadingStrip()
        } else {
            ProviderRow(
                name = "STRAVA",
                state = uiState.status?.strava,
                onConnect = { viewModel.connect("strava", openUrl) },
                onSync = { viewModel.sync("strava") },
            )
            HairlineRule()
            ProviderRow(
                name = "SPOTIFY",
                state = uiState.status?.spotify,
                onConnect = { viewModel.connect("spotify", openUrl) },
                onSync = { viewModel.sync("spotify") },
            )
            HairlineRule()
            StaticRow("HEALTH CONNECT", "LATER STEP")
            HairlineRule()
        }

        uiState.syncMessage?.let {
            Spacer(Modifier.height(12.dp))
            Text(it, style = MaterialTheme.typography.labelSmall.copy(color = Steel),
                modifier = Modifier.padding(horizontal = 20.dp))
        }
        uiState.error?.let {
            Spacer(Modifier.height(12.dp))
            Text(it, style = MaterialTheme.typography.labelSmall.copy(color = GateRed),
                modifier = Modifier.padding(horizontal = 20.dp))
        }
    }
}

@Composable
private fun ProviderRow(
    name: String,
    state: IntegrationState?,
    onConnect: () -> Unit,
    onSync: () -> Unit,
) {
    Row(
        modifier = Modifier.fillMaxWidth().padding(horizontal = 20.dp, vertical = 14.dp),
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Column {
            Text(name, style = MaterialTheme.typography.labelLarge)
            Text(
                when {
                    state == null -> "--"
                    state.connected -> "CONNECTED" +
                        (state.lastSyncedAt?.let { " · LAST SYNC $it" } ?: "")
                    else -> "NOT CONNECTED"
                },
                style = MaterialTheme.typography.labelSmall.copy(color = Graphite),
            )
        }
        if (state?.connected == true) {
            Text(
                "SYNC NOW",
                style = MaterialTheme.typography.titleSmall.copy(color = Steel),
                modifier = Modifier.clickable(onClick = onSync),
            )
        } else {
            Text(
                "CONNECT",
                style = MaterialTheme.typography.titleSmall.copy(color = GateRed),
                modifier = Modifier.clickable(onClick = onConnect),
            )
        }
    }
}

@Composable
private fun StaticRow(name: String, status: String) {
    Column(Modifier.fillMaxWidth().padding(horizontal = 20.dp, vertical = 14.dp)) {
        Text(name, style = MaterialTheme.typography.labelLarge)
        Spacer(Modifier.height(2.dp))
        Text(status, style = MaterialTheme.typography.labelSmall.copy(color = Graphite))
    }
}
