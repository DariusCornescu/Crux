package com.darius.crux.ui.viewmodel

import androidx.lifecycle.SavedStateHandle
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.darius.crux.data.model.Report
import com.darius.crux.data.repository.RepoResult
import com.darius.crux.data.repository.ReportsRepository
import com.darius.crux.network.MetricDayDTO
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

data class ReportDetailUiState(
    val report: Report? = null,
    val isLoading: Boolean = true,
    val error: String? = null,
    // null hides the WEEK IN NUMBERS section — a metrics failure never blocks the report body.
    val metrics: List<MetricDayDTO>? = null,
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

            // Independent of the report fetch above — a metrics failure must never
            // block or error out the report body, it just hides WEEK IN NUMBERS.
            val metrics = when (val result = repository.getReportMetrics(reportId)) {
                is RepoResult.Success -> result.data
                is RepoResult.Error -> null
            }
            _uiState.value = _uiState.value.copy(metrics = metrics)
        }
    }
}
