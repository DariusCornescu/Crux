package com.darius.crux.ui.viewmodel

import androidx.lifecycle.SavedStateHandle
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.darius.crux.data.model.Report
import com.darius.crux.data.repository.RepoResult
import com.darius.crux.data.repository.ReportsRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

data class ReportDetailUiState(
    val report: Report? = null,
    val isLoading: Boolean = true,
    val error: String? = null,
)

/** reportId arrives through the nav back-stack entry's SavedStateHandle. */
class ReportDetailViewModel(savedStateHandle: SavedStateHandle) : ViewModel() {
    private val repository = ReportsRepository()
    private val reportId: Long = savedStateHandle.get<Long>("reportId") ?: -1L

    private val _uiState = MutableStateFlow(ReportDetailUiState())
    val uiState: StateFlow<ReportDetailUiState> = _uiState.asStateFlow()

    init {
        load()
    }

    fun load() {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(isLoading = true, error = null)
            when (val result = repository.getReport(reportId)) {
                is RepoResult.Success -> _uiState.value =
                    ReportDetailUiState(report = result.data, isLoading = false)
                is RepoResult.Error -> _uiState.value =
                    _uiState.value.copy(isLoading = false, error = result.message)
            }
        }
    }
}
