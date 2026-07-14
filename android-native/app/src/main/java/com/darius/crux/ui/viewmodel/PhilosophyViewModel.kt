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
    val quoteAuthor: String? = null,
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
            val cachedAuthor = CruxPreferences.lastQuoteAuthor()
            val cachedReflection = CruxPreferences.lastReflection()
            _uiState.value = _uiState.value.copy(
                isLoading = true,
                error = null,
                quote = _uiState.value.quote ?: cachedQuote,
                quoteAuthor = _uiState.value.quoteAuthor ?: cachedAuthor,
                reflection = _uiState.value.reflection ?: cachedReflection,
            )

            var lastError: String? = null
            var quoteAuthor = cachedAuthor

            val quote = when (val r = repo.getQuoteToday()) {
                is RepoResult.Success -> {
                    quoteAuthor = r.data.author
                    CruxPreferences.saveQuote(r.data.text, r.data.author)
                    r.data.text
                }
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
                quoteAuthor = quoteAuthor,
                reflection = reflection,
                archive = archive,
                isLoading = false,
                error = if (quote == null && reflection == null && archive.isEmpty()) lastError else null,
            )
        }
    }
}
