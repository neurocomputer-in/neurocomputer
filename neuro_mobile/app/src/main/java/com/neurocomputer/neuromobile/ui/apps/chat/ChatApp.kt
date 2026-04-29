package com.neurocomputer.neuromobile.ui.apps.chat

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.hilt.navigation.compose.hiltViewModel

@Composable
fun ChatApp(
    cid: String,
    agentId: String,
    modifier: Modifier = Modifier,
) {
    val viewModel = hiltViewModel<ChatViewModel, ChatViewModel.Factory>(
        key = cid,
        creationCallback = { factory -> factory.create(cid, agentId) }
    )
    val state by viewModel.state.collectAsState()

    Column(modifier.fillMaxSize().background(Color(0xFF0d0d14))) {
        // AgentDropdown omitted in v1 — complex required params (agents list, selectedAgent, callbacks)

        ChatMessageList(
            messages = state.messages,
            modifier = Modifier.weight(1f),
        )
        ChatInputBar(
            value = state.inputText,
            onValueChange = viewModel::onInputChange,
            onSend = viewModel::send,
        )
    }
}
