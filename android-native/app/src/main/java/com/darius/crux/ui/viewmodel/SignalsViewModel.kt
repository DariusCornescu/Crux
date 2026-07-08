package com.darius.crux.ui.viewmodel

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.darius.crux.data.repository.RepoResult
import com.darius.crux.data.repository.SignalsRepository
import com.darius.crux.network.SignalsDTO
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

data class SignalsUiState(
    val data: SignalsDTO? = null,
    val isLoading: Boolean = true,
    val error: String? = null,
)

class SignalsViewModel : ViewModel() {
    private val repository = SignalsRepository()

    private val _uiState = MutableStateFlow(SignalsUiState())
    val uiState: StateFlow<SignalsUiState> = _uiState.asStateFlow()

    init {
        load()
    }

    fun load() {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(isLoading = true, error = null)
            when (val result = repository.getSignalsDetail()) {
                is RepoResult.Success -> _uiState.value =
                    SignalsUiState(data = result.data, isLoading = false)
                is RepoResult.Error -> _uiState.value =
                    _uiState.value.copy(isLoading = false, error = result.message)
            }
        }
    }
}
