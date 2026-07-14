package com.darius.crux.ui.viewmodel

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.darius.crux.data.repository.ObjectiveRepository
import com.darius.crux.data.repository.RepoResult
import com.darius.crux.network.ObjectiveDTO
import com.darius.crux.network.ObjectiveInDTO
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

data class ObjectiveUiState(
    val objective: ObjectiveDTO? = null,
    val isLoading: Boolean = true,
    val isSaving: Boolean = false,
    val error: String? = null,
)

class ObjectiveViewModel : ViewModel() {
    private val repo = ObjectiveRepository()

    private val _uiState = MutableStateFlow(ObjectiveUiState())
    val uiState: StateFlow<ObjectiveUiState> = _uiState.asStateFlow()

    init {
        load()
    }

    fun load() {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(isLoading = true, error = null)
            when (val r = repo.getCurrent()) {
                is RepoResult.Success -> _uiState.value = ObjectiveUiState(objective = r.data, isLoading = false)
                is RepoResult.Error -> _uiState.value = _uiState.value.copy(isLoading = false, error = r.message)
            }
        }
    }

    fun save(name: String, elevationM: Int?, targetDate: String, vertGoalM: Int) {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(isSaving = true, error = null)
            when (val r = repo.save(ObjectiveInDTO(name, elevationM, targetDate, vertGoalM))) {
                is RepoResult.Success -> _uiState.value =
                    ObjectiveUiState(objective = r.data, isLoading = false, isSaving = false)
                is RepoResult.Error -> _uiState.value = _uiState.value.copy(isSaving = false, error = r.message)
            }
        }
    }
}
