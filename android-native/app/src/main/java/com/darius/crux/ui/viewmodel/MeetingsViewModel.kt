package com.darius.crux.ui.viewmodel

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.darius.crux.data.repository.CalendarRepository
import com.darius.crux.data.repository.RepoResult
import com.darius.crux.network.CalendarEventDTO
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import java.time.Instant
import java.time.OffsetDateTime

data class MeetingsUiState(
    val upcoming: List<CalendarEventDTO> = emptyList(),   // ascending, soonest first
    val past: List<CalendarEventDTO> = emptyList(),       // descending, most recent first
    val isLoading: Boolean = true,
    val error: String? = null,
)

class MeetingsViewModel : ViewModel() {
    private val repo = CalendarRepository()

    private val _uiState = MutableStateFlow(MeetingsUiState())
    val uiState: StateFlow<MeetingsUiState> = _uiState.asStateFlow()

    init {
        load()
    }

    fun load() {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(isLoading = true, error = null)
            when (val r = repo.getEvents()) {
                is RepoResult.Success -> {
                    val now = Instant.now()
                    val withInstant = r.data.mapNotNull { e ->
                        runCatching { OffsetDateTime.parse(e.start).toInstant() }.getOrNull()?.let { e to it }
                    }
                    val upcoming = withInstant.filter { !it.second.isBefore(now) }
                        .sortedBy { it.second }.map { it.first }
                    val past = withInstant.filter { it.second.isBefore(now) }
                        .sortedByDescending { it.second }.map { it.first }
                    _uiState.value = MeetingsUiState(upcoming = upcoming, past = past, isLoading = false)
                }
                is RepoResult.Error -> _uiState.value =
                    _uiState.value.copy(isLoading = false, error = r.message)
            }
        }
    }
}
