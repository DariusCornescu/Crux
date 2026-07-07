package com.darius.crux.ui.viewmodel

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.darius.crux.data.model.IntegrationsStatus
import com.darius.crux.data.repository.IntegrationsRepository
import com.darius.crux.data.repository.RepoResult
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

data class SettingsUiState(
    val status: IntegrationsStatus? = null,
    val isLoading: Boolean = true,
    val syncMessage: String? = null,
    val error: String? = null,
)

class SettingsViewModel : ViewModel() {
    private val repository = IntegrationsRepository()

    private val _uiState = MutableStateFlow(SettingsUiState())
    val uiState: StateFlow<SettingsUiState> = _uiState.asStateFlow()

    init {
        refresh()
    }

    fun refresh() {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(isLoading = true, error = null)
            when (val result = repository.getStatus()) {
                is RepoResult.Success -> _uiState.value =
                    _uiState.value.copy(status = result.data, isLoading = false)
                is RepoResult.Error -> _uiState.value =
                    _uiState.value.copy(isLoading = false, error = result.message)
            }
        }
    }

    /** Fetches the OAuth URL, then hands it to the screen to open in the browser. */
    fun connect(provider: String, openUrl: (String) -> Unit) {
        viewModelScope.launch {
            when (val result = repository.getAuthorizeUrl(provider)) {
                is RepoResult.Success -> openUrl(result.data)
                is RepoResult.Error -> _uiState.value = _uiState.value.copy(error = result.message)
            }
        }
    }

    fun sync(provider: String) {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(syncMessage = "SYNCING ${provider.uppercase()}…")
            when (val result = repository.triggerSync(provider)) {
                is RepoResult.Success -> {
                    _uiState.value = _uiState.value.copy(
                        syncMessage = "${provider.uppercase()} +${result.data}")
                    refresh()
                }
                is RepoResult.Error -> _uiState.value =
                    _uiState.value.copy(syncMessage = null, error = result.message)
            }
        }
    }
}
