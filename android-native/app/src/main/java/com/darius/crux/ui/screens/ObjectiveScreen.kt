package com.darius.crux.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.clickable
import androidx.compose.foundation.text.BasicTextField
import androidx.compose.foundation.text.KeyboardOptions
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
import androidx.compose.ui.graphics.SolidColor
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import androidx.lifecycle.viewmodel.compose.viewModel
import com.darius.crux.network.ObjectiveDTO
import com.darius.crux.ui.components.HairlineRule
import com.darius.crux.ui.components.LoadingStrip
import com.darius.crux.ui.components.MeetSheetScreen
import com.darius.crux.ui.components.SectionHeader
import com.darius.crux.ui.theme.ChalkShade
import com.darius.crux.ui.theme.GateRed
import com.darius.crux.ui.theme.Graphite
import com.darius.crux.ui.theme.Ink
import com.darius.crux.ui.theme.Scree
import com.darius.crux.ui.theme.Space
import com.darius.crux.ui.viewmodel.ObjectiveViewModel
import java.util.Locale

/**
 * OBJECTIVE — the training goal. A summit + date with a days countdown and a
 * vertical-banked progress bar, plus a form to set/edit it. Reached from the
 * dashboard OBJECTIVE teaser.
 */
@Composable
fun ObjectiveScreen(
    onBack: () -> Unit,
    viewModel: ObjectiveViewModel = viewModel(),
) {
    val uiState by viewModel.uiState.collectAsState()

    MeetSheetScreen(title = "OBJECTIVE", onBack = onBack) {
        when {
            uiState.isLoading && uiState.objective == null -> LoadingStrip()
            else -> {
                uiState.objective?.let { obj ->
                    ObjectiveHeadline(obj)
                    HairlineRule()
                }
                ObjectiveForm(
                    existing = uiState.objective,
                    isSaving = uiState.isSaving,
                    error = uiState.error,
                    onSave = viewModel::save,
                )
            }
        }
        Spacer(Modifier.height(Space.xxl))
    }
}

@Composable
private fun ObjectiveHeadline(obj: ObjectiveDTO) {
    Column(Modifier.fillMaxWidth().padding(horizontal = Space.screenH, vertical = Space.sectionV)) {
        val summit = obj.elevation_m?.let { "${obj.name} · $it M" } ?: obj.name
        SectionHeader("COUNTDOWN", subtitle = summit, accent = GateRed)
        Spacer(Modifier.height(Space.md))
        Row(verticalAlignment = Alignment.Bottom) {
            Text(obj.days_to_go.coerceAtLeast(0).toString(), style = MaterialTheme.typography.displayLarge)
            Spacer(Modifier.width(Space.sm))
            Text("DAYS", style = MaterialTheme.typography.titleSmall.copy(color = Ink),
                modifier = Modifier.padding(bottom = Space.md))
        }
        Text("TO ${obj.name.uppercase(Locale.US)} · ${obj.target_date}",
            style = MaterialTheme.typography.labelSmall.copy(color = Graphite))

        Spacer(Modifier.height(Space.lg))
        Row(Modifier.fillMaxWidth()) {
            Text("VERT BANKED", style = MaterialTheme.typography.labelSmall.copy(color = Graphite),
                modifier = Modifier.weight(1f))
            Text("${fmt(obj.banked_m)} / ${fmt(obj.vert_goal_m)} M",
                style = MaterialTheme.typography.labelMedium.copy(color = Ink))
        }
        Spacer(Modifier.height(Space.sm))
        val frac = if (obj.vert_goal_m > 0) (obj.banked_m.toFloat() / obj.vert_goal_m).coerceIn(0f, 1f) else 0f
        Box(Modifier.fillMaxWidth().height(10.dp).background(ChalkShade)) {
            Box(Modifier.fillMaxWidth(frac).fillMaxHeight().background(Scree))
        }
    }
}

@Composable
private fun ObjectiveForm(
    existing: ObjectiveDTO?,
    isSaving: Boolean,
    error: String?,
    onSave: (String, Int?, String, Int) -> Unit,
) {
    var name by remember(existing) { mutableStateOf(existing?.name ?: "") }
    var elevation by remember(existing) { mutableStateOf(existing?.elevation_m?.toString() ?: "") }
    var target by remember(existing) { mutableStateOf(existing?.target_date ?: "") }
    var vertGoal by remember(existing) { mutableStateOf(existing?.vert_goal_m?.toString() ?: "") }
    var localError by remember(existing) { mutableStateOf<String?>(null) }

    Column(Modifier.fillMaxWidth().padding(horizontal = Space.screenH, vertical = Space.sectionV)) {
        SectionHeader(if (existing == null) "SET OBJECTIVE" else "EDIT")
        Spacer(Modifier.height(Space.md))

        Field("SUMMIT", name) { name = it }
        Field("HEIGHT (M)", elevation, numeric = true) { elevation = it }
        Field("TARGET DATE (YYYY-MM-DD)", target) { target = it }
        Field("VERT GOAL (M)", vertGoal, numeric = true) { vertGoal = it }

        (localError ?: error)?.let {
            Spacer(Modifier.height(Space.sm))
            Text(it, style = MaterialTheme.typography.labelSmall.copy(color = GateRed))
        }

        Spacer(Modifier.height(Space.lg))
        Text(
            if (isSaving) "SAVING…" else "SAVE",
            style = MaterialTheme.typography.titleSmall.copy(color = if (isSaving) Graphite else GateRed),
            modifier = Modifier.clickable(enabled = !isSaving) {
                val goal = vertGoal.trim().toIntOrNull()
                localError = when {
                    name.isBlank() -> "SUMMIT REQUIRED"
                    !Regex("""\d{4}-\d{2}-\d{2}""").matches(target.trim()) -> "DATE MUST BE YYYY-MM-DD"
                    goal == null || goal <= 0 -> "VERT GOAL REQUIRED"
                    else -> null
                }
                if (localError == null && goal != null) {
                    onSave(name.trim(), elevation.trim().toIntOrNull(), target.trim(), goal)
                }
            },
        )
    }
}

@Composable
private fun Field(label: String, value: String, numeric: Boolean = false, onChange: (String) -> Unit) {
    Column(Modifier.fillMaxWidth().padding(vertical = Space.sm)) {
        Text(label, style = MaterialTheme.typography.labelSmall.copy(color = Graphite))
        Spacer(Modifier.height(Space.xs))
        BasicTextField(
            value = value,
            onValueChange = onChange,
            singleLine = true,
            textStyle = MaterialTheme.typography.bodyMedium.copy(color = Ink),
            cursorBrush = SolidColor(GateRed),
            keyboardOptions = if (numeric) KeyboardOptions(keyboardType = KeyboardType.Number) else KeyboardOptions.Default,
            modifier = Modifier.fillMaxWidth().padding(vertical = Space.xs),
        )
        HairlineRule()
    }
}

private fun fmt(n: Int): String = "%,d".format(Locale.US, n)
