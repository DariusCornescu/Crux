package com.darius.crux.ui.viewmodel

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.darius.crux.data.model.DashboardData
import com.darius.crux.data.repository.DashboardRepository
import com.darius.crux.data.repository.RepoResult
import com.darius.crux.network.UpcomingEventDTO
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

data class DashboardUiState(
    val data: DashboardData? = null,
    val isLoading: Boolean = true,
    val error: String? = null,
)

class DashboardViewModel : ViewModel() {
    private val repository = DashboardRepository()

    private val _uiState = MutableStateFlow(DashboardUiState())
    val uiState: StateFlow<DashboardUiState> = _uiState.asStateFlow()

    // NEXT UP agenda and daily quote load independently of the main dashboard
    // fetch above — either can fail/lag without blocking or gating the rest.
    private val _agenda = MutableStateFlow<List<UpcomingEventDTO>?>(null)
    val agenda: StateFlow<List<UpcomingEventDTO>?> = _agenda.asStateFlow()

    private val _quote = MutableStateFlow<String?>(null)
    val quote: StateFlow<String?> = _quote.asStateFlow()

    init {
        load()
        loadAgenda()
        loadQuote()
    }

    fun load() {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(isLoading = true, error = null)
            when (val result = repository.getDashboard()) {
                is RepoResult.Success -> _uiState.value =
                    DashboardUiState(data = result.data, isLoading = false)
                is RepoResult.Error -> _uiState.value =
                    _uiState.value.copy(isLoading = false, error = result.message)
            }
        }
    }

    private fun loadAgenda() {
        viewModelScope.launch {
            _agenda.value = try {
                when (val result = repository.getUpcomingEvents()) {
                    is RepoResult.Success -> result.data
                    is RepoResult.Error -> null
                }
            } catch (e: Exception) {
                null
            }
        }
    }

    private fun loadQuote() {
        viewModelScope.launch {
            _quote.value = try {
                when (val result = repository.getQuoteToday()) {
                    is RepoResult.Success -> result.data.text
                    is RepoResult.Error -> null
                }
            } catch (e: Exception) {
                null
            }
        }
    }
}
