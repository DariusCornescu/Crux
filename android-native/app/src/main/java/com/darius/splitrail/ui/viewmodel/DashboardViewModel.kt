package com.darius.splitrail.ui.viewmodel

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.darius.splitrail.data.model.DashboardData
import com.darius.splitrail.data.repository.DashboardRepository
import com.darius.splitrail.data.repository.RepoResult
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

    init {
        load()
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
}
