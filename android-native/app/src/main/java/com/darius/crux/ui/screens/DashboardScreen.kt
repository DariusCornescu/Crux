package com.darius.crux.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.lifecycle.viewmodel.compose.viewModel
import com.darius.crux.data.model.Conditions
import com.darius.crux.data.model.DashboardData
import com.darius.crux.network.GithubHeatmapDTO
import com.darius.crux.network.ObjectiveDTO
import com.darius.crux.network.ReadinessDTO
import com.darius.crux.network.TrainingGridDTO
import com.darius.crux.network.UpcomingEventDTO
import com.darius.crux.ui.components.AgendaBlock
import com.darius.crux.ui.components.AltiInstrument
import com.darius.crux.ui.components.ContributionGrid
import com.darius.crux.ui.components.ErrorStrip
import com.darius.crux.ui.components.HairlineRule
import com.darius.crux.ui.components.HeroReadout
import com.darius.crux.ui.components.LoadingStrip
import com.darius.crux.ui.components.MeetSheetScreen
import com.darius.crux.ui.components.MoodTrace
import com.darius.crux.ui.components.RailTape
import com.darius.crux.ui.components.ReadinessGauge
import com.darius.crux.ui.components.SectionHeader
import com.darius.crux.ui.components.StripInstrument
import com.darius.crux.ui.components.TrainingGrid
import com.darius.crux.ui.theme.ChalkShade
import com.darius.crux.ui.theme.GateRed
import com.darius.crux.ui.theme.Graphite
import com.darius.crux.ui.theme.Ink
import com.darius.crux.ui.theme.Scree
import com.darius.crux.ui.theme.Space
import com.darius.crux.ui.theme.Steel
import com.darius.crux.ui.viewmodel.DashboardViewModel
import java.util.Locale

@Composable
fun DashboardScreen(
    onOpenSignals: () -> Unit = {},
    onOpenPhilosophy: () -> Unit = {},
    onOpenMeetings: () -> Unit = {},
    onOpenObjective: () -> Unit = {},
    viewModel: DashboardViewModel = viewModel(),
) {
    val uiState by viewModel.uiState.collectAsState()
    val agenda by viewModel.agenda.collectAsState()
    val quote by viewModel.quote.collectAsState()
    val quoteAuthor by viewModel.quoteAuthor.collectAsState()
    val mood by viewModel.mood.collectAsState()
    val heatmap by viewModel.heatmap.collectAsState()
    val readiness by viewModel.readiness.collectAsState()
    val trainingGrid by viewModel.trainingGrid.collectAsState()
    val objective by viewModel.objective.collectAsState()
    var expandedAgendaIndex by remember { mutableStateOf<Int?>(null) }

    MeetSheetScreen(
        title = "CRUX",
        accent = Ink,
        trailing = { WeekTag(uiState.data?.week, uiState.data?.isDemo == true) },
    ) {
        quote?.let {
            Column(
                Modifier.fillMaxWidth().clickable(onClick = onOpenPhilosophy)
                    .padding(horizontal = Space.screenH, vertical = Space.lg),
            ) {
                Text(it, style = MaterialTheme.typography.bodyLarge)
                quoteAuthor?.let { author ->
                    Spacer(Modifier.height(Space.xs))
                    Text("— $author", style = MaterialTheme.typography.labelMedium.copy(color = Graphite))
                }
                Spacer(Modifier.height(Space.sm))
                Text("PHILOSOPHY →", style = MaterialTheme.typography.labelSmall.copy(color = GateRed))
            }
            HairlineRule()
        }

        val objectiveNow = objective
        if (objectiveNow != null) {
            ObjectiveTeaser(objectiveNow, onOpenObjective)
        } else {
            ObjectiveSetPrompt(onOpenObjective)
        }
        HairlineRule()

        when {
            uiState.isLoading && uiState.data == null -> LoadingStrip()
            uiState.error != null && uiState.data == null ->
                ErrorStrip(uiState.error ?: "NO SIGNAL", onRetry = viewModel::load)
            uiState.data != null -> DashboardBody(
                data = uiState.data!!,
                agenda = agenda,
                expandedAgendaIndex = expandedAgendaIndex,
                onToggleAgenda = { index ->
                    expandedAgendaIndex = if (expandedAgendaIndex == index) null else index
                },
                moodPhrase = mood,
                onOpenSignals = onOpenSignals,
                onOpenMeetings = onOpenMeetings,
                readiness = readiness,
            )
        }

        // CODE — GitHub contributions as another discipline (only once synced).
        heatmap?.let { h ->
            if (h.source != "none") {
                HairlineRule()
                CodeBlock(h)
            }
        }

        // TRAINING — the discipline grid alongside CODE.
        trainingGrid?.let { tg ->
            if (tg.days.isNotEmpty()) {
                HairlineRule()
                TrainingBlock(tg)
            }
        }

        Spacer(Modifier.height(Space.xxl))
    }
}

@Composable
private fun CodeBlock(h: GithubHeatmapDTO) {
    Column(Modifier.fillMaxWidth().padding(horizontal = Space.screenH, vertical = Space.sectionV)) {
        SectionHeader("CODE", subtitle = if (h.source == "events") "APPROX" else null, accent = Steel)
        Spacer(Modifier.height(Space.md))
        ContributionGrid(h.days)
        Spacer(Modifier.height(Space.sm))
        Text(
            "STREAK ${h.current_streak} · LONGEST ${h.longest_streak} · ${h.total} CONTRIB",
            style = MaterialTheme.typography.labelMedium.copy(color = Ink),
        )
    }
}

@Composable
private fun TrainingBlock(tg: TrainingGridDTO) {
    Column(Modifier.fillMaxWidth().padding(horizontal = Space.screenH, vertical = Space.sectionV)) {
        SectionHeader("TRAINING", subtitle = "${tg.active_days} DAYS", accent = Steel)
        Spacer(Modifier.height(Space.md))
        TrainingGrid(tg.days)
        Spacer(Modifier.height(Space.sm))
        Text(
            "${tg.total_sessions} SESSIONS · ${String.format(Locale.US, "%.1f", tg.total_km)} KM · ${tg.active_days} DAYS",
            style = MaterialTheme.typography.labelMedium.copy(color = Ink),
        )
    }
}

@Composable
private fun ObjectiveSetPrompt(onOpen: () -> Unit) {
    Column(
        Modifier.fillMaxWidth().clickable(onClick = onOpen)
            .padding(horizontal = Space.screenH, vertical = Space.lg),
    ) {
        SectionHeader(
            "OBJECTIVE",
            trailing = {
                Text("SET A GOAL →", style = MaterialTheme.typography.labelSmall.copy(color = GateRed))
            },
        )
    }
}

@Composable
private fun ObjectiveTeaser(obj: ObjectiveDTO, onOpen: () -> Unit) {
    Column(
        Modifier.fillMaxWidth().clickable(onClick = onOpen)
            .padding(horizontal = Space.screenH, vertical = Space.lg),
    ) {
        SectionHeader(
            "OBJECTIVE",
            subtitle = obj.name,
            accent = GateRed,
            trailing = {
                Text("${obj.days_to_go.coerceAtLeast(0)} DAYS →",
                    style = MaterialTheme.typography.labelSmall.copy(color = GateRed))
            },
        )
        Spacer(Modifier.height(Space.md))
        val frac = if (obj.vert_goal_m > 0) (obj.banked_m.toFloat() / obj.vert_goal_m).coerceIn(0f, 1f) else 0f
        Box(Modifier.fillMaxWidth().height(Space.sm).background(ChalkShade)) {
            Box(Modifier.fillMaxWidth(frac).fillMaxHeight().background(Scree))
        }
    }
}

@Composable
private fun DashboardBody(
    data: DashboardData,
    agenda: List<UpcomingEventDTO>?,
    expandedAgendaIndex: Int?,
    onToggleAgenda: (Int) -> Unit,
    moodPhrase: String?,
    onOpenSignals: () -> Unit,
    onOpenMeetings: () -> Unit,
    readiness: ReadinessDTO?,
) {
    // Hero — the one Anton readout: the week's aerobic base, the rebuild's headline number.
    HeroReadout(
        value = String.format(Locale.US, "%.1f", data.strip.weekKm),
        unit = "KM",
        caption = "WK ${data.week} · AEROBIC BASE",
    )
    HairlineRule()

    // COND + mood barograph — the tappable window into SIGNALS.
    Column(Modifier.fillMaxWidth().clickable(onClick = onOpenSignals)) {
        ConditionsStrip(data.conditions, moodPhrase)
        MoodTrace(
            data.moodTrend,
            modifier = Modifier.padding(horizontal = Space.screenH).padding(bottom = Space.md),
        )
    }
    HairlineRule()

    readiness?.let {
        Column(Modifier.fillMaxWidth().padding(horizontal = Space.screenH, vertical = Space.sectionV)) {
            SectionHeader("READINESS")
            Spacer(Modifier.height(Space.md))
            ReadinessGauge(it)
        }
        HairlineRule()
    }

    // THE RAIL — signature element
    Column(Modifier.padding(horizontal = Space.screenH, vertical = Space.lg)) {
        SectionHeader("THE RAIL", subtitle = "WK ${data.week}", accent = Ink)
        Spacer(Modifier.height(Space.xs))
        RailTape(data.rail)
    }
    HairlineRule()

    if (!agenda.isNullOrEmpty()) {
        AgendaBlock(agenda, expandedAgendaIndex, onToggleAgenda, onOpenAll = onOpenMeetings)
        HairlineRule()
    }

    StripInstrument(data.strip)
    HairlineRule()

    AltiInstrument(data.alti)
}

@Composable
private fun WeekTag(week: Int?, isDemo: Boolean) {
    Row(verticalAlignment = Alignment.CenterVertically) {
        if (isDemo) {
            Text("DEMO SIGNAL", style = MaterialTheme.typography.labelSmall.copy(color = GateRed))
            Spacer(Modifier.width(Space.sm))
        }
        Text(
            week?.let { "WK $it" } ?: "--",
            style = MaterialTheme.typography.labelMedium.copy(color = Graphite),
        )
    }
}

@Composable
private fun ConditionsStrip(c: Conditions, moodPhrase: String?) {
    val sleep = c.sleepMin?.let { "${it / 60}:${String.format(Locale.US, "%02d", it % 60)}" } ?: "--"
    val rhr = c.restingHr?.toString() ?: "--"
    val steps = formatSteps(c.steps)
    val mood = moodPhrase ?: "…"

    Row(
        modifier = Modifier.fillMaxWidth().padding(horizontal = Space.screenH).padding(bottom = Space.md),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Text("COND", style = MaterialTheme.typography.labelSmall.copy(color = GateRed))
        Spacer(Modifier.width(Space.sm))
        Text("SLEEP $sleep · RHR $rhr · STEPS $steps · MOOD $mood", style = MaterialTheme.typography.labelSmall)
    }
}

/** Compact step total: 8241 -> "8.2K", small counts stay literal, null -> "--". */
private fun formatSteps(steps: Int?): String = when {
    steps == null -> "--"
    steps >= 1000 -> String.format(Locale.US, "%.1fK", steps / 1000.0)
    else -> steps.toString()
}
