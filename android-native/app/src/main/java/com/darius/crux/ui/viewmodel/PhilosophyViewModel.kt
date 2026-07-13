package com.darius.crux.ui.viewmodel

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.darius.crux.data.local.CruxPreferences
import com.darius.crux.data.repository.PhilosophyRepository
import com.darius.crux.data.repository.RepoResult
import com.darius.crux.network.QuoteDTO
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

data class PhilosophyUiState(
    val quote: String? = null,
    val reflection: String? = null,
    val archive: List<QuoteDTO> = emptyList(),
    val isLoading: Boolean = true,
    val error: String? = null,
)

class PhilosophyViewModel : ViewModel() {
    private val repo = PhilosophyRepository()

    private val _uiState = MutableStateFlow(PhilosophyUiState())
    val uiState: StateFlow<PhilosophyUiState> = _uiState.asStateFlow()

    init {
        load()
    }

    fun load() {
        viewModelScope.launch {
            // Seed from the on-device cache first so the zone is never blank.
            val cachedQuote = CruxPreferences.lastQuote()
            val cachedReflection = CruxPreferences.lastReflection()
            _uiState.value = _uiState.value.copy(
                isLoading = true,
                error = null,
                quote = _uiState.value.quote ?: cachedQuote,
                reflection = _uiState.value.reflection ?: cachedReflection,
            )

            var lastError: String? = null

            val quote = when (val r = repo.getQuoteToday()) {
                is RepoResult.Success -> r.data.text.also { CruxPreferences.saveQuote(it) }
                is RepoResult.Error -> { lastError = r.message; cachedQuote }
            }
            val reflection = when (val r = repo.getReflectionToday()) {
                is RepoResult.Success -> r.data.text.also { CruxPreferences.saveReflection(it) }
                is RepoResult.Error -> { lastError = r.message; cachedReflection }
            }
            val archive = when (val r = repo.getQuoteArchive()) {
                is RepoResult.Success -> r.data
                is RepoResult.Error -> { lastError = r.message; emptyList() }
            }

            _uiState.value = PhilosophyUiState(
                quote = quote,
                reflection = reflection,
                archive = archive,
                isLoading = false,
                // Only surface an error when there is genuinely nothing to show.
                error = if (quote == null && reflection == null && archive.isEmpty()) lastError else null,
            )
        }
    }
}
