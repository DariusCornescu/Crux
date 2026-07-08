package com.darius.crux.ui.viewmodel

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.darius.crux.data.model.ChatMessage
import com.darius.crux.data.repository.ChatRepository
import com.darius.crux.data.repository.RepoResult
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.Job
import kotlinx.coroutines.cancelAndJoin
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
    private var streamJob: Job? = null // active streaming collection, so CLEAR can abort it

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

        // Optimistic user turn + an empty assistant row that fills in token-by-token.
        val optimistic = ChatMessage(id = localId--, role = "user", content = trimmed, createdAt = "")
        val assistantId = localId--
        val placeholder = ChatMessage(id = assistantId, role = "assistant", content = "", createdAt = "")
        _uiState.value = _uiState.value.copy(
            messages = _uiState.value.messages + optimistic + placeholder,
            isSending = true, error = null,
        )

        streamJob = viewModelScope.launch {
            var receivedAny = false
            try {
                repository.streamMessage(trimmed).collect { token ->
                    receivedAny = true
                    updateAssistantMessage(assistantId) { it.copy(content = it.content + token) }
                }
                if (receivedAny) {
                    _uiState.value = _uiState.value.copy(isSending = false)
                } else {
                    // Completed cleanly but empty (EOF right after headers) — treat as failure.
                    fallbackSend(trimmed, assistantId)
                }
            } catch (e: Exception) {
                if (e is CancellationException) {
                    // Cancelled (CLEAR, or scope death) — unstick the input, then propagate.
                    _uiState.value = _uiState.value.copy(isSending = false)
                    throw e
                }
                if (receivedAny) {
                    // Partial reply already on screen — mark it broken off, don't re-send.
                    updateAssistantMessage(assistantId) { it.copy(content = it.content + " — SIGNAL LOST") }
                    _uiState.value = _uiState.value.copy(isSending = false)
                } else {
                    // Streaming never got off the ground — fall back to the plain endpoint.
                    fallbackSend(trimmed, assistantId)
                }
            }
        }
    }

    private suspend fun fallbackSend(trimmed: String, assistantId: Long) {
        when (val result = repository.send(trimmed)) {
            is RepoResult.Success -> {
                updateAssistantMessage(assistantId) { it.copy(content = result.data) }
                _uiState.value = _uiState.value.copy(isSending = false)
            }
            is RepoResult.Error -> _uiState.value = _uiState.value.copy(
                messages = _uiState.value.messages.filterNot { it.id == assistantId },
                isSending = false,
                error = result.message,
            )
        }
    }

    private fun updateAssistantMessage(id: Long, transform: (ChatMessage) -> ChatMessage) {
        _uiState.value = _uiState.value.copy(
            messages = _uiState.value.messages.map { if (it.id == id) transform(it) else it },
        )
    }

    fun clearHistory() {
        viewModelScope.launch {
            // Order matters: abort any in-flight stream FIRST (the backend persists the
            // partial row on interrupt), THEN delete everything, THEN drop local state.
            streamJob?.cancelAndJoin()
            streamJob = null
            // Covers the narrow race where cancellation lands mid-fallbackSend, whose own
            // isSending reset is skipped by the propagating CancellationException.
            _uiState.value = _uiState.value.copy(isSending = false)
            when (val result = repository.clearHistory()) {
                is RepoResult.Success -> _uiState.value =
                    _uiState.value.copy(messages = emptyList(), error = null)
                is RepoResult.Error -> _uiState.value = _uiState.value.copy(error = result.message)
            }
        }
    }
}
