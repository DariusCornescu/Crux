package com.darius.crux

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import com.darius.crux.ui.navigation.NavGraph
import com.darius.crux.ui.theme.CruxTheme

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            CruxTheme {
                NavGraph()
            }
        }
    }
}
