package com.darius.splitrail.ui.viewmodel

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.darius.splitrail.data.model.ChatMessage
import com.darius.splitrail.data.repository.ChatRepository
import com.darius.splitrail.data.repository.RepoResult
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

data class ChatUiState(
    val messages: List<ChatMessage> = emptyList(),
    val isLoading: Boolean = true,
    val isSending: Boolean = false,
    val error: String? = null,
)

class ChatViewModel : ViewModel() {
    private val repository = ChatRepository()
    private var localId = -1L // negative ids for optimistic messages

    private val _uiState = MutableStateFlow(ChatUiState())
    val uiState: StateFlow<ChatUiState> = _uiState.asStateFlow()

    init {
        loadHistory()
    }

    fun loadHistory() {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(isLoading = true, error = null)
            when (val result = repository.getHistory()) {
                is RepoResult.Success -> _uiState.value =
                    _uiState.value.copy(messages = result.data, isLoading = false)
                is RepoResult.Error -> _uiState.value =
                    _uiState.value.copy(isLoading = false, error = result.message)
            }
        }
    }

    fun send(text: String) {
        val trimmed = text.trim()
        if (trimmed.isEmpty() || _uiState.value.isSending) return

        // Optimistic user turn
        val optimistic = ChatMessage(id = localId--, role = "user", content = trimmed, createdAt = "")
        _uiState.value = _uiState.value.copy(
            messages = _uiState.value.messages + optimistic,
            isSending = true, error = null,
        )

        viewModelScope.launch {
            when (val result = repository.send(trimmed)) {
                is RepoResult.Success -> _uiState.value = _uiState.value.copy(
                    messages = _uiState.value.messages +
                        ChatMessage(id = localId--, role = "assistant", content = result.data, createdAt = ""),
                    isSending = false,
                )
                is RepoResult.Error -> _uiState.value =
                    _uiState.value.copy(isSending = false, error = result.message)
            }
        }
    }
}
