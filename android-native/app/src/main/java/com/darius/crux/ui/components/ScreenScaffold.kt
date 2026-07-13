package com.darius.crux.ui.components

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ColumnScope
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import com.darius.crux.ui.theme.Graphite
import com.darius.crux.ui.theme.Ink
import com.darius.crux.ui.theme.Space

/**
 * The single top bar for every screen — one definition kills the per-screen drift
 * (the copy-pasted Row, the 12-vs-10dp spacer). Optional back affordance, subtitle,
 * and a right-aligned trailing action. Ends in the app's only divider, a hairline.
 */
@Composable
fun MeetSheetHeader(
    title: String,
    modifier: Modifier = Modifier,
    onBack: (() -> Unit)? = null,
    subtitle: String? = null,
    accent: Color = Ink,
    trailing: (@Composable () -> Unit)? = null,
) {
    Column(modifier.fillMaxWidth()) {
        Row(
            modifier = Modifier.fillMaxWidth().padding(horizontal = Space.screenH),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                if (onBack != null) {
                    Text(
                        "← BACK",
                        style = MaterialTheme.typography.titleSmall.copy(color = Graphite),
                        modifier = Modifier.clickable(onClick = onBack),
                    )
                    Spacer(Modifier.width(Space.md))
                }
                Text(title, style = MaterialTheme.typography.titleSmall.copy(color = accent))
                if (subtitle != null) {
                    Spacer(Modifier.width(Space.md))
                    Text("▏$subtitle", style = MaterialTheme.typography.titleSmall.copy(color = Graphite))
                }
            }
            if (trailing != null) trailing()
        }
        Spacer(Modifier.height(Space.md))
        HairlineRule()
    }
}

/**
 * A whole scrolling screen: [MeetSheetHeader] over a content column. Pass
 * `scroll = false` when the content manages its own scroll (a LazyColumn, or a
 * screen with a pinned footer). Screens with a pinned input bar (Chat) use
 * [MeetSheetHeader] directly instead of this scaffold.
 */
@Composable
fun MeetSheetScreen(
    title: String,
    modifier: Modifier = Modifier,
    onBack: (() -> Unit)? = null,
    subtitle: String? = null,
    accent: Color = Ink,
    scroll: Boolean = true,
    trailing: (@Composable () -> Unit)? = null,
    content: @Composable ColumnScope.() -> Unit,
) {
    val base = Modifier.fillMaxSize().padding(top = Space.topInset)
    val outer = if (scroll) base.verticalScroll(rememberScrollState()) else base
    Column(modifier = modifier.then(outer)) {
        MeetSheetHeader(
            title = title,
            onBack = onBack,
            subtitle = subtitle,
            accent = accent,
            trailing = trailing,
        )
        content()
    }
}
