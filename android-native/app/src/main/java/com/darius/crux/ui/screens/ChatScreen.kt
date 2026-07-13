package com.darius.crux.ui.screens

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.imePadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.text.BasicTextField
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.SolidColor
import androidx.lifecycle.viewmodel.compose.viewModel
import com.darius.crux.data.model.ChatMessage
import com.darius.crux.ui.components.ErrorStrip
import com.darius.crux.ui.components.HairlineRule
import com.darius.crux.ui.components.LoadingStrip
import com.darius.crux.ui.components.MarkdownLite
import com.darius.crux.ui.components.MeetSheetHeader
import com.darius.crux.ui.theme.GateRed
import com.darius.crux.ui.theme.Graphite
import com.darius.crux.ui.theme.Space
import com.darius.crux.ui.theme.Steel
import com.darius.crux.ui.viewmodel.ChatViewModel
import kotlinx.coroutines.delay

@Composable
fun ChatScreen(viewModel: ChatViewModel = viewModel()) {
    val uiState by viewModel.uiState.collectAsState()
    val listState = rememberLazyListState()
    var input by remember { mutableStateOf("") }

    // Keyed on the last row's length too, so the list keeps following streamed tokens.
    LaunchedEffect(uiState.messages.size, uiState.messages.lastOrNull()?.content?.length) {
        if (uiState.messages.isNotEmpty()) {
            listState.animateScrollToItem(uiState.messages.size - 1)
        }
    }

    Column(Modifier.fillMaxSize().imePadding().padding(top = Space.topInset)) {
        MeetSheetHeader(
            title = "CHAT",
            subtitle = "ASK YOUR DATA",
            accent = Steel,
            trailing = {
                if (uiState.messages.isNotEmpty()) {
                    ClearHistoryAction(onConfirm = viewModel::clearHistory)
                }
            },
        )

        when {
            uiState.isLoading -> LoadingStrip()
            uiState.error != null && uiState.messages.isEmpty() ->
                ErrorStrip(uiState.error ?: "NO SIGNAL", onRetry = viewModel::loadHistory)
            uiState.messages.isEmpty() -> Text(
                "Ask anything about your training, sleep or mood — " +
                    "answers come from your own data.",
                style = MaterialTheme.typography.bodySmall,
                modifier = Modifier.padding(Space.screenH).weight(1f),
            )
            else -> LazyColumn(state = listState, modifier = Modifier.weight(1f)) {
                items(uiState.messages, key = { it.id }) { message ->
                    MessageRow(message)
                    HairlineRule()
                }
            }
        }

        // Inline error while history is still shown
        if (uiState.error != null && uiState.messages.isNotEmpty()) {
            Text(
                uiState.error ?: "",
                style = MaterialTheme.typography.labelSmall.copy(color = GateRed),
                modifier = Modifier.padding(horizontal = Space.screenH, vertical = Space.sm),
            )
        }

        InputBar(
            value = input,
            enabled = !uiState.isSending,
            onValueChange = { input = it },
            onSend = {
                viewModel.send(input)
                input = ""
            },
        )
    }
}

/** Engraved CLEAR action — tap once to arm (SURE?, GateRed), tap again to confirm.
 *  Arms for 3s only; untouched, it quietly steps back down to CLEAR. */
@Composable
private fun ClearHistoryAction(onConfirm: () -> Unit) {
    var confirming by remember { mutableStateOf(false) }

    LaunchedEffect(confirming) {
        if (confirming) {
            delay(3000)
            confirming = false
        }
    }

    Text(
        if (confirming) "SURE?" else "CLEAR",
        style = MaterialTheme.typography.labelSmall.copy(color = if (confirming) GateRed else Graphite),
        modifier = Modifier.clickable {
            if (confirming) {
                confirming = false
                onConfirm()
            } else {
                confirming = true
            }
        },
    )
}

/** Messages as timing-sheet entries — mono role tag, hairline separation. No bubbles. */
@Composable
private fun MessageRow(message: ChatMessage) {
    Column(Modifier.fillMaxWidth().padding(horizontal = Space.screenH, vertical = Space.md)) {
        Text(
            if (message.role == "user") "YOU" else "CRUX",
            style = MaterialTheme.typography.labelSmall.copy(
                color = if (message.role == "user") Graphite else Steel),
        )
        Spacer(Modifier.height(Space.xs))
        if (message.role == "assistant") {
            MarkdownLite(message.content)
        } else {
            Text(message.content, style = MaterialTheme.typography.bodyMedium)
        }
    }
}

@Composable
private fun InputBar(
    value: String,
    enabled: Boolean,
    onValueChange: (String) -> Unit,
    onSend: () -> Unit,
) {
    Column {
        HairlineRule()
        Row(
            modifier = Modifier.fillMaxWidth().padding(horizontal = Space.screenH, vertical = Space.md),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            BasicTextField(
                value = value,
                onValueChange = onValueChange,
                textStyle = MaterialTheme.typography.bodyMedium,
                cursorBrush = SolidColor(GateRed),
                modifier = Modifier.weight(1f),
                decorationBox = { innerTextField ->
                    if (value.isEmpty()) {
                        Text(
                            "ASK YOUR DATA…",
                            style = MaterialTheme.typography.labelSmall.copy(color = Graphite),
                        )
                    }
                    innerTextField()
                },
            )
            Spacer(Modifier.width(Space.xl))
            Text(
                if (enabled) "SEND" else "…",
                style = MaterialTheme.typography.titleSmall.copy(
                    color = if (enabled && value.isNotBlank()) GateRed else Graphite),
                modifier = Modifier.clickable(enabled = enabled && value.isNotBlank(), onClick = onSend),
            )
        }
    }
}
