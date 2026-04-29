package com.neurocomputer.neuromobile.ui.apps.chat

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.neurocomputer.neuromobile.data.service.ChatDataChannelService
import com.neurocomputer.neuromobile.data.service.ChatMessage
import com.neurocomputer.neuromobile.domain.model.Message
import dagger.assisted.Assisted
import dagger.assisted.AssistedFactory
import dagger.assisted.AssistedInject
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import java.util.UUID

data class ChatState(
    val messages: List<Message> = emptyList(),
    val inputText: String = "",
    val isLoading: Boolean = false,
)

@HiltViewModel(assistedFactory = ChatViewModel.Factory::class)
class ChatViewModel @AssistedInject constructor(
    @Assisted("cid") val cid: String,
    @Assisted("agentId") val agentId: String,
    private val chatDataChannelService: ChatDataChannelService,
) : ViewModel() {

    private val _state = MutableStateFlow(ChatState())
    val state: StateFlow<ChatState> = _state.asStateFlow()

    @AssistedFactory
    interface Factory {
        fun create(@Assisted("cid") cid: String, @Assisted("agentId") agentId: String): ChatViewModel
    }

    init {
        observeMessages()
        connectIfNeeded()
    }

    private fun connectIfNeeded() {
        viewModelScope.launch {
            val current = chatDataChannelService.connectionState.value
            if (!current.connected || current.conversationId != cid) {
                chatDataChannelService.connect(cid)
            }
        }
    }

    private fun observeMessages() {
        viewModelScope.launch {
            chatDataChannelService.messages.collect { msg ->
                when (msg) {
                    is ChatMessage.TextMessage -> {
                        if (msg.sender == "user") return@collect
                        val newMsg = Message(
                            id = msg.messageId,
                            text = msg.text,
                            isUser = false,
                        )
                        _state.value = _state.value.copy(
                            messages = _state.value.messages + newMsg,
                            isLoading = false,
                        )
                    }
                    is ChatMessage.VoiceMessage -> {
                        if (msg.sender == "user") return@collect
                        val newMsg = Message(
                            id = msg.messageId,
                            text = "",
                            isUser = false,
                            isVoice = true,
                            audioUrl = msg.audioUrl,
                        )
                        _state.value = _state.value.copy(
                            messages = _state.value.messages + newMsg,
                            isLoading = false,
                        )
                    }
                    is ChatMessage.SystemMessage -> {
                        if (msg.topic == "task.done" || msg.topic == "node.done") {
                            _state.value = _state.value.copy(isLoading = false)
                        }
                    }
                    else -> Unit
                }
            }
        }
    }

    fun onInputChange(text: String) {
        _state.value = _state.value.copy(inputText = text)
    }

    fun send() {
        val text = _state.value.inputText.trim()
        if (text.isEmpty()) return

        // Add user message locally
        val userMsg = Message(
            id = "user_${UUID.randomUUID()}",
            text = text,
            isUser = true,
        )
        _state.value = _state.value.copy(
            messages = _state.value.messages + userMsg,
            inputText = "",
            isLoading = true,
        )

        viewModelScope.launch {
            // Ensure connected
            val current = chatDataChannelService.connectionState.value
            if (!current.connected || current.conversationId != cid) {
                val connected = chatDataChannelService.connect(cid)
                if (!connected) {
                    val errMsg = Message(
                        id = "error_${UUID.randomUUID()}",
                        text = "Failed to connect to chat",
                        isUser = false,
                    )
                    _state.value = _state.value.copy(
                        messages = _state.value.messages + errMsg,
                        isLoading = false,
                    )
                    return@launch
                }
            }

            val success = chatDataChannelService.sendTextMessage(text)
            if (!success) {
                val errMsg = Message(
                    id = "error_${UUID.randomUUID()}",
                    text = "Failed to send message",
                    isUser = false,
                )
                _state.value = _state.value.copy(
                    messages = _state.value.messages + errMsg,
                    isLoading = false,
                )
            }
        }

        // Timeout: clear loading after 45s
        viewModelScope.launch {
            kotlinx.coroutines.delay(45_000)
            if (_state.value.isLoading) {
                _state.value = _state.value.copy(isLoading = false)
            }
        }
    }
}
