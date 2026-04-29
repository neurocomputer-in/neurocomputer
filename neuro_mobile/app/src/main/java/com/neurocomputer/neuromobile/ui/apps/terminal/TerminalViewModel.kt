package com.neurocomputer.neuromobile.ui.apps.terminal

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.neurocomputer.neuromobile.data.service.WebSocketService
import com.neurocomputer.neuromobile.data.service.WsMessage
import dagger.assisted.Assisted
import dagger.assisted.AssistedFactory
import dagger.assisted.AssistedInject
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

data class TerminalState(
    val lines: List<List<AnsiSpan>> = emptyList(),
    val inputText: String = "",
    val connected: Boolean = false,
)

@HiltViewModel(assistedFactory = TerminalViewModel.Factory::class)
class TerminalViewModel @AssistedInject constructor(
    @Assisted val cid: String,
    private val webSocketService: WebSocketService,
) : ViewModel() {

    @AssistedFactory
    interface Factory {
        fun create(cid: String): TerminalViewModel
    }

    private val _state = MutableStateFlow(TerminalState())
    val state: StateFlow<TerminalState> = _state.asStateFlow()

    init {
        connectIfNeeded()
        observeMessages()
    }

    private fun connectIfNeeded() {
        val connected = webSocketService.connectionState.value
        if (!connected) {
            webSocketService.connect(cid)
        }
    }

    private fun observeMessages() {
        viewModelScope.launch {
            webSocketService.connectionState.collect { connected ->
                _state.update { it.copy(connected = connected) }
            }
        }
        viewModelScope.launch {
            webSocketService.messages.collect { msg ->
                when (msg) {
                    is WsMessage.Connected -> _state.update { it.copy(connected = true) }
                    is WsMessage.Disconnected -> _state.update { it.copy(connected = false) }
                    is WsMessage.Text -> appendLine(msg.text)
                    is WsMessage.Json -> {
                        // Terminal output may arrive as topic "terminal.output" or "output"
                        if (msg.topic in setOf("terminal.output", "output", "pty.output")) {
                            appendLine(msg.data)
                        }
                    }
                    is WsMessage.Error -> appendLine("[error] ${msg.error}")
                }
            }
        }
    }

    private fun appendLine(raw: String) {
        // Split by newlines so each logical line is a separate entry
        val newLines = raw.split("\n").filter { it.isNotEmpty() }.map { AnsiParser.parse(it) }
        if (newLines.isNotEmpty()) {
            _state.update { it.copy(lines = it.lines + newLines) }
        }
    }

    fun onInputChange(text: String) {
        _state.update { it.copy(inputText = text) }
    }

    fun sendLine() {
        val line = _state.value.inputText
        if (line.isEmpty()) return
        _state.update { it.copy(inputText = "") }
        viewModelScope.launch {
            webSocketService.sendMessage("$line\n", cid)
        }
    }
}
