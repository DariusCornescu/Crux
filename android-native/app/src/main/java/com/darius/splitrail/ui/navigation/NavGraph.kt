package com.darius.splitrail.ui.navigation

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.navigation.NavHostController
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.currentBackStackEntryAsState
import androidx.navigation.compose.rememberNavController
import com.darius.splitrail.ui.components.HairlineRule
import com.darius.splitrail.ui.screens.ChatScreen
import com.darius.splitrail.ui.screens.DashboardScreen
import com.darius.splitrail.ui.screens.ReportsScreen
import com.darius.splitrail.ui.screens.SettingsScreen
import com.darius.splitrail.ui.theme.GateRed
import com.darius.splitrail.ui.theme.Graphite
import com.darius.splitrail.ui.theme.Ink

private data class Dest(val route: String, val label: String)

private val DESTS = listOf(
    Dest("dashboard", "DASH"),
    Dest("chat", "CHAT"),
    Dest("reports", "REPORTS"),
    Dest("settings", "SETTINGS"),
)

@Composable
fun NavGraph() {
    val nav = rememberNavController()
    Scaffold(
        containerColor = MaterialTheme.colorScheme.background,
        bottomBar = { BezelNav(nav) },
    ) { padding ->
        NavHost(
            navController = nav,
            startDestination = "dashboard",
            modifier = Modifier.padding(padding),
        ) {
            composable("dashboard") { DashboardScreen() }
            composable("chat") { ChatScreen() }
            composable("reports") { ReportsScreen() }
            composable("settings") { SettingsScreen() }
        }
    }
}

/** Bottom nav as a machined bezel: hairline on top, mono caps, red index mark on the active item. */
@Composable
private fun BezelNav(nav: NavHostController) {
    val backStack by nav.currentBackStackEntryAsState()
    val currentRoute = backStack?.destination?.route

    Column(Modifier.background(MaterialTheme.colorScheme.background).navigationBarsPadding()) {
        HairlineRule()
        Row(Modifier.fillMaxWidth()) {
            DESTS.forEach { dest ->
                val selected = currentRoute == dest.route
                Column(
                    horizontalAlignment = Alignment.CenterHorizontally,
                    modifier = Modifier
                        .weight(1f)
                        .clickable {
                            nav.navigate(dest.route) {
                                popUpTo("dashboard") { saveState = true }
                                launchSingleTop = true
                                restoreState = true
                            }
                        }
                        .padding(vertical = 12.dp),
                ) {
                    // Index mark — like the lubber line on an instrument bezel
                    Box(
                        Modifier
                            .width(24.dp)
                            .height(2.dp)
                            .background(if (selected) GateRed else MaterialTheme.colorScheme.background),
                    )
                    Spacer(Modifier.height(6.dp))
                    Text(
                        dest.label,
                        style = MaterialTheme.typography.labelSmall.copy(
                            color = if (selected) Ink else Graphite,
                        ),
                    )
                }
            }
        }
    }
}
