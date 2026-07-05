package com.darius.splitrail

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import com.darius.splitrail.ui.navigation.NavGraph
import com.darius.splitrail.ui.theme.SplitrailTheme

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            SplitrailTheme {
                NavGraph()
            }
        }
    }
}
