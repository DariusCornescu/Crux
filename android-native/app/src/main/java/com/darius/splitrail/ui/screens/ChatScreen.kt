package com.darius.splitrail.ui.screens

import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.darius.splitrail.ui.components.HairlineRule
import com.darius.splitrail.ui.components.InstrumentLabel
import com.darius.splitrail.ui.theme.Steel

@Composable
fun ChatScreen() {
    Column(Modifier.fillMaxSize().padding(horizontal = 20.dp, vertical = 18.dp)) {
        InstrumentLabel("CHAT", "ASK YOUR DATA", Steel)
        Spacer(Modifier.height(10.dp))
        HairlineRule()
        Spacer(Modifier.height(14.dp))
        Text(
            "On-demand Q&A over your training, sleep and mood data. Wired to the backend at build step 6.",
            style = MaterialTheme.typography.bodySmall,
        )
    }
}
