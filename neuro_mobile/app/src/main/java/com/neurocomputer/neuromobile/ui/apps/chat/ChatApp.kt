package com.neurocomputer.neuromobile.ui.apps.chat

import android.Manifest
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.alpha
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.hilt.navigation.compose.hiltViewModel
import com.google.accompanist.permissions.ExperimentalPermissionsApi
import com.google.accompanist.permissions.isGranted
import com.google.accompanist.permissions.rememberPermissionState
import com.neurocomputer.neuromobile.data.APP_LIST

/** Agents we host ourselves — full feature set (model picker, voice call). */
private val NATIVE_AGENTS = setOf("neuro", "neuroupwork", "nl_dev")

@OptIn(ExperimentalPermissionsApi::class)
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
    var voicePanelExpanded by remember { mutableStateOf(false) }

    val isNative = agentId.lowercase() in NATIVE_AGENTS
    val app = remember(agentId) {
        APP_LIST.firstOrNull { it.agentType?.equals(agentId, ignoreCase = true) == true }
    }
    val displayName = app?.name ?: agentId.replaceFirstChar { it.uppercase() }
    val logoResId = app?.iconResId

    val micPermission = rememberPermissionState(Manifest.permission.RECORD_AUDIO)
    var pendingMicAction by remember { mutableStateOf<(() -> Unit)?>(null) }
    LaunchedEffect(micPermission.status.isGranted) {
        if (micPermission.status.isGranted) {
            pendingMicAction?.invoke()
            pendingMicAction = null
        }
    }
    val ensureMicThen: (() -> Unit) -> Unit = { action ->
        if (micPermission.status.isGranted) action()
        else { pendingMicAction = action; micPermission.launchPermissionRequest() }
    }

    Box(modifier.fillMaxSize().background(Color(0xFF0d0d14))) {
        if (state.voiceCallActive && voicePanelExpanded) {
            VoiceExpandedView(
                title = displayName,
                isMuted = state.voiceCallMuted,
                transcripts = state.messages,
                interimUser = state.voiceInterimUser,
                onCollapse = { voicePanelExpanded = false },
                onToggleMute = viewModel::toggleVoiceMute,
                onEndCall = { viewModel.endVoiceCall(); voicePanelExpanded = false },
            )
        } else {
            Column(Modifier.fillMaxSize()) {
                Box(Modifier.weight(1f)) {
                    if (state.messages.isEmpty() && !state.isLoading) {
                        EmptyChatState(
                            agentName = displayName,
                            logoResId = logoResId,
                            isNative = isNative,
                        )
                    } else {
                        ChatMessageList(
                            messages = state.messages,
                            isLoading = state.isLoading,
                            modifier = Modifier.fillMaxSize(),
                        )
                    }
                }
                if (state.voiceCallConnecting) VoiceConnectingBar()
                if (state.voiceCallActive) {
                    VoiceCollapsedBar(
                        isMuted = state.voiceCallMuted,
                        onExpand = { voicePanelExpanded = true },
                        onToggleMute = viewModel::toggleVoiceMute,
                        onEndCall = { viewModel.endVoiceCall(); voicePanelExpanded = false },
                    )
                }
                ChatInputBar(
                    value = state.inputText,
                    onValueChange = viewModel::onInputChange,
                    onSend = viewModel::send,
                    isRecording = state.isRecording,
                    recordingSeconds = state.recordingSeconds,
                    onStartRecording = { ensureMicThen(viewModel::startRecording) },
                    onCancelRecording = viewModel::cancelRecording,
                    onSendVoice = viewModel::stopAndSendVoiceMessage,
                    onStartVoiceCall = { ensureMicThen(viewModel::startVoiceCall) },
                    showModelPicker = isNative,
                    showVoiceCall = isNative,
                    modelLabel = modelDisplayLabel(state.llmProvider, state.llmModel),
                    onOpenModelPicker = viewModel::openLlmPicker,
                )
            }
        }
    }

    if (state.showLlmPicker) {
        LlmPickerSheet(
            currentProvider = state.llmProvider,
            currentModel = state.llmModel,
            providers = state.llmProviders,
            onDismiss = viewModel::closeLlmPicker,
            onConfirm = viewModel::updateLlmSettings,
        )
    }
}

private fun modelDisplayLabel(provider: String, model: String): String {
    if (model.isBlank() && provider.isBlank()) return "Auto"
    val short = model.substringAfterLast("/").substringBefore(":").take(10)
    return short.ifBlank { provider.take(10) }
}

@Composable
private fun EmptyChatState(
    agentName: String,
    logoResId: Int?,
    isNative: Boolean,
) {
    Box(
        modifier = Modifier
            .fillMaxSize()
            .padding(32.dp),
        contentAlignment = Alignment.Center,
    ) {
        // Faded logo watermark
        if (logoResId != null) {
            Image(
                painter = painterResource(id = logoResId),
                contentDescription = null,
                modifier = Modifier
                    .size(200.dp)
                    .alpha(0.07f),
            )
        }

        Column(
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.spacedBy(10.dp),
        ) {
            Text(
                text = "Welcome to $agentName",
                color = Color.White,
                fontSize = 24.sp,
                fontWeight = FontWeight.SemiBold,
            )
            Text(
                text = if (isNative) "How can I help you today?"
                       else "Send a message to get started",
                color = Color(0xFF8888aa),
                fontSize = 14.sp,
            )
        }
    }
}

@Composable
private fun VoiceConnectingBar() {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .background(Color(0xFF0f1117))
            .padding(horizontal = 16.dp, vertical = 10.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(10.dp),
    ) {
        CircularProgressIndicator(modifier = Modifier.size(16.dp), color = Color(0xFF8B5CF6), strokeWidth = 2.dp)
        Text("Connecting to voice…", color = Color(0xFF8888aa), fontSize = 13.sp)
    }
}
