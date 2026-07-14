package com.darius.crux.ui.viewmodel

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.darius.crux.data.local.CruxPreferences
import com.darius.crux.data.model.DashboardData
import com.darius.crux.data.repository.DashboardRepository
import com.darius.crux.data.repository.GithubRepository
import com.darius.crux.data.repository.RepoResult
import com.darius.crux.network.GithubHeatmapDTO
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
    private val githubRepository = GithubRepository()

    private val _uiState = MutableStateFlow(DashboardUiState())
    val uiState: StateFlow<DashboardUiState> = _uiState.asStateFlow()

    private val _heatmap = MutableStateFlow<GithubHeatmapDTO?>(null)
    val heatmap: StateFlow<GithubHeatmapDTO?> = _heatmap.asStateFlow()

    // NEXT UP agenda and daily quote load independently of the main dashboard
    // fetch above — either can fail/lag without blocking or gating the rest.
    private val _agenda = MutableStateFlow<List<UpcomingEventDTO>?>(null)
    val agenda: StateFlow<List<UpcomingEventDTO>?> = _agenda.asStateFlow()

    private val _quote = MutableStateFlow<String?>(null)
    val quote: StateFlow<String?> = _quote.asStateFlow()

    private val _quoteAuthor = MutableStateFlow<String?>(null)
    val quoteAuthor: StateFlow<String?> = _quoteAuthor.asStateFlow()

    private val _mood = MutableStateFlow<String?>(null)
    val mood: StateFlow<String?> = _mood.asStateFlow()

    init {
        load()
    }

    fun load() {
        // RETRY re-enters here — refresh agenda/quote/mood too (idempotent, non-blocking),
        // otherwise a failed offline start would leave them null forever.
        loadAgenda()
        loadQuote()
        loadMood()
        loadHeatmap()
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
            // Seed from the on-device cache so a previously-seen quote never vanishes
            // on a cold or offline start (the old code nulled it on any failure).
            if (_quote.value == null) {
                _quote.value = CruxPreferences.lastQuote()
                _quoteAuthor.value = CruxPreferences.lastQuoteAuthor()
            }
            try {
                when (val result = repository.getQuoteToday()) {
                    is RepoResult.Success -> {
                        _quote.value = result.data.text
                        _quoteAuthor.value = result.data.author
                        CruxPreferences.saveQuote(result.data.text, result.data.author)
                    }
                    is RepoResult.Error -> { /* keep the cached value */ }
                }
            } catch (e: Exception) {
                /* keep the cached value */
            }
        }
    }

    private fun loadMood() {
        viewModelScope.launch {
            _mood.value = try {
                when (val result = repository.getMoodCurrent()) {
                    is RepoResult.Success -> result.data.phrase
                    is RepoResult.Error -> null
                }
            } catch (e: Exception) {
                null
            }
        }
    }

    private fun loadHeatmap() {
        viewModelScope.launch {
            _heatmap.value = try {
                when (val result = githubRepository.getHeatmap(weeks = 20)) {
                    is RepoResult.Success -> result.data
                    is RepoResult.Error -> null
                }
            } catch (e: Exception) {
                null
            }
        }
    }
}
