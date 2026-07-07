package com.darius.crux.ui.viewmodel

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.darius.crux.data.model.Report
import com.darius.crux.data.repository.RepoResult
import com.darius.crux.data.repository.ReportsRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

data class ReportsUiState(
    val reports: List<Report> = emptyList(),
    val isLoading: Boolean = true,
    val isGenerating: Boolean = false,
    val error: String? = null,
)

class ReportsViewModel : ViewModel() {
    private val repository = ReportsRepository()

    private val _uiState = MutableStateFlow(ReportsUiState())
    val uiState: StateFlow<ReportsUiState> = _uiState.asStateFlow()

    init {
        load()
    }

    fun load() {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(isLoading = true, error = null)
            when (val result = repository.getReports()) {
                is RepoResult.Success -> _uiState.value =
                    _uiState.value.copy(reports = result.data, isLoading = false)
                is RepoResult.Error -> _uiState.value =
                    _uiState.value.copy(isLoading = false, error = result.message)
            }
        }
    }

    fun generate() {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(isGenerating = true, error = null)
            when (val result = repository.generateReport()) {
                is RepoResult.Success -> {
                    _uiState.value = _uiState.value.copy(isGenerating = false)
                    load()
                }
                is RepoResult.Error -> _uiState.value =
                    _uiState.value.copy(isGenerating = false, error = result.message)
            }
        }
    }
}
