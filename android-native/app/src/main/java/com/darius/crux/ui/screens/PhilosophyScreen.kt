package com.darius.crux.ui.screens

import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.lifecycle.viewmodel.compose.viewModel
import com.darius.crux.network.QuoteDTO
import com.darius.crux.ui.components.EmptyStrip
import com.darius.crux.ui.components.ErrorStrip
import com.darius.crux.ui.components.HairlineRule
import com.darius.crux.ui.components.LoadingStrip
import com.darius.crux.ui.components.MeetSheetScreen
import com.darius.crux.ui.components.SectionHeader
import com.darius.crux.ui.theme.Graphite
import com.darius.crux.ui.theme.Ink
import com.darius.crux.ui.theme.Space
import com.darius.crux.ui.viewmodel.PhilosophyViewModel
import java.time.LocalDate
import java.time.format.DateTimeFormatter
import java.util.Locale

private val ARCHIVE_DAY_FMT: DateTimeFormatter = DateTimeFormatter.ofPattern("MMM d", Locale.US)

/**
 * PHILOSOPHY — the reflective zone. Today's quote as a hero band, an LLM
 * reflection tying training to mood, and a scrollable archive of past quotes.
 * Reached by tapping the quote band on the Dashboard.
 */
@Composable
fun PhilosophyScreen(
    onBack: () -> Unit,
    viewModel: PhilosophyViewModel = viewModel(),
) {
    val uiState by viewModel.uiState.collectAsState()

    MeetSheetScreen(title = "PHILOSOPHY", onBack = onBack) {
        when {
            uiState.isLoading && uiState.quote == null && uiState.reflection == null -> LoadingStrip()
            uiState.error != null && uiState.quote == null && uiState.reflection == null ->
                ErrorStrip(uiState.error ?: "NO SIGNAL", onRetry = viewModel::load)
            else -> {
                uiState.quote?.let { quote ->
                    Column(Modifier.fillMaxWidth().padding(horizontal = Space.screenH, vertical = Space.sectionV)) {
                        SectionHeader("TODAY")
                        Spacer(Modifier.height(Space.md))
                        Text(quote, style = MaterialTheme.typography.bodyLarge)
                        uiState.quoteAuthor?.let { author ->
                            Spacer(Modifier.height(Space.sm))
                            Text("— $author", style = MaterialTheme.typography.labelMedium.copy(color = Graphite))
                        }
                    }
                    HairlineRule()
                }

                uiState.reflection?.let { reflection ->
                    Column(Modifier.fillMaxWidth().padding(horizontal = Space.screenH, vertical = Space.sectionV)) {
                        SectionHeader("REFLECTION")
                        Spacer(Modifier.height(Space.md))
                        Text(reflection, style = MaterialTheme.typography.bodyMedium.copy(color = Ink))
                        Spacer(Modifier.height(Space.sm))
                        Text("— CRUX", style = MaterialTheme.typography.labelMedium.copy(color = Graphite))
                    }
                    HairlineRule()
                }

                ArchiveSection(uiState.archive)
            }
        }
        Spacer(Modifier.height(Space.xxl))
    }
}

@Composable
private fun ArchiveSection(archive: List<QuoteDTO>) {
    Column(Modifier.fillMaxWidth().padding(horizontal = Space.screenH, vertical = Space.sectionV)) {
        SectionHeader("ARCHIVE")
        Spacer(Modifier.height(Space.md))

        if (archive.isEmpty()) {
            Text("NO ARCHIVE YET", style = MaterialTheme.typography.labelSmall.copy(color = Graphite))
        } else {
            archive.forEachIndexed { index, q ->
                if (index != 0) Spacer(Modifier.height(Space.lg))
                Text(formatDay(q.day), style = MaterialTheme.typography.labelSmall.copy(color = Graphite))
                Spacer(Modifier.height(Space.xs))
                Text(q.text, style = MaterialTheme.typography.bodyMedium.copy(color = Ink))
                q.author?.let { author ->
                    Spacer(Modifier.height(Space.xs))
                    Text("— $author", style = MaterialTheme.typography.labelSmall.copy(color = Graphite))
                }
            }
        }
    }
}

private fun formatDay(iso: String): String =
    runCatching { LocalDate.parse(iso).format(ARCHIVE_DAY_FMT).uppercase(Locale.US) }
        .getOrDefault(iso)
