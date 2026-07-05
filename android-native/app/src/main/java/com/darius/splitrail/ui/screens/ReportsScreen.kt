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
import com.darius.splitrail.ui.theme.GateRed

@Composable
fun ReportsScreen() {
    Column(Modifier.fillMaxSize().padding(horizontal = 20.dp, vertical = 18.dp)) {
        InstrumentLabel("REPORTS", "WEEKLY ANALYSIS", GateRed)
        Spacer(Modifier.height(10.dp))
        HairlineRule()
        Spacer(Modifier.height(14.dp))
        Text(
            "LLM-generated weekly reports land here (build step 5): one section per effort mode, plus recovery and mood context.",
            style = MaterialTheme.typography.bodySmall,
        )
    }
}
