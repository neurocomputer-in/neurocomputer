package com.neurocomputer.neuromobile.ui.screens

import androidx.compose.animation.*
import androidx.compose.animation.core.*
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.Image
import androidx.compose.foundation.clickable
import androidx.compose.foundation.gestures.detectDragGestures
import androidx.compose.foundation.gestures.detectTapGestures
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.BasicTextField
import androidx.compose.foundation.text.KeyboardActions
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.Send
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.alpha
import androidx.compose.ui.draw.blur
import androidx.compose.ui.draw.clip
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.SolidColor
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.IntOffset
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.neurocomputer.neuromobile.data.repository.BackendHealthState
import com.neurocomputer.neuromobile.data.repository.BackendUrlRepository
import com.neurocomputer.neuromobile.data.repository.StartupRepository
import com.neurocomputer.neuromobile.data.service.VoiceService
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.RequestBody.Companion.toRequestBody
import com.neurocomputer.neuromobile.data.service.VoiceConnectionState
import com.neurocomputer.neuromobile.data.service.WebSocketService
import com.neurocomputer.neuromobile.data.service.ChatDataChannelService
import com.neurocomputer.neuromobile.data.service.ChatMessage
import com.neurocomputer.neuromobile.data.service.OpenClawService
import com.neurocomputer.neuromobile.data.service.LiveKitService
import com.neurocomputer.neuromobile.data.service.WsMessage
import io.livekit.android.room.track.VideoTrack
import androidx.compose.ui.unit.DpOffset
import io.livekit.android.compose.ui.VideoTrackView
import io.livekit.android.compose.ui.ScaleType
import io.livekit.android.compose.local.RoomLocal
import androidx.compose.runtime.CompositionLocalProvider
import io.livekit.android.room.Room
import com.neurocomputer.neuromobile.R
import com.neurocomputer.neuromobile.domain.model.AgentInfo
import com.neurocomputer.neuromobile.domain.model.AgentType
import com.neurocomputer.neuromobile.domain.model.ConversationSummary
import com.neurocomputer.neuromobile.domain.model.Message
import com.neurocomputer.neuromobile.ui.components.*
import com.neurocomputer.neuromobile.ui.theme.NeuroColors
import androidx.core.view.WindowCompat
import androidx.core.view.WindowInsetsCompat
import androidx.core.view.WindowInsetsControllerCompat
import android.content.pm.ActivityInfo
import android.util.Log
import androidx.compose.runtime.DisposableEffect
import android.app.Activity
import android.content.Intent
import com.neurocomputer.neuromobile.data.service.OverlayService
import androidx.compose.ui.platform.LocalContext
import androidx.activity.compose.rememberLauncherForActivityResult
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.*
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import java.text.SimpleDateFormat
import java.util.*
import javax.inject.Inject
import kotlin.math.roundToInt

enum class TouchMode { NONE, TOUCHPAD, TABLET }

@HiltViewModel
class ConversationViewModel @Inject constructor(
    private val webSocketService: WebSocketService,
    private val chatDataChannelService: ChatDataChannelService,
    private val voiceService: VoiceService,
    private val backendUrlRepository: BackendUrlRepository,
    private val startupRepository: StartupRepository,
    private val openClawService: OpenClawService,
    private val liveKitService: LiveKitService,
    private val orientationService: com.neurocomputer.neuromobile.domain.OrientationService,
    val rotationLockState: com.neurocomputer.neuromobile.domain.RotationLockState,
    @dagger.hilt.android.qualifiers.ApplicationContext private val context: android.content.Context
) : ViewModel() {

    fun toggleRotationLock() {
        val newVal = rotationLockState.toggle()
        orientationService.setLock(newVal)
    }

    fun onScreenRotationChanged(surfaceRotation: Int) {
        orientationService.onRotationChanged(surfaceRotation)
    }

    val liveKitServicePublic: LiveKitService get() = liveKitService

    val remoteCursorPosition = liveKitService.serverCursorPosition
    val remoteScreenDims = liveKitService.serverScreenDimensions


    private val _messages = MutableStateFlow<List<Message>>(emptyList())
    val messages: StateFlow<List<Message>> = _messages.asStateFlow()

    private val _inputText = MutableStateFlow("")
    val inputText: StateFlow<String> = _inputText.asStateFlow()

    private val _isLoading = MutableStateFlow(false)
    val isLoading: StateFlow<Boolean> = _isLoading.asStateFlow()

    private val _isTabLoading = MutableStateFlow(false)
    val isTabLoading: StateFlow<Boolean> = _isTabLoading.asStateFlow()

    val isConnected: StateFlow<Boolean> = chatDataChannelService.connectionState.map { it.connected }.stateIn(viewModelScope, SharingStarted.Eagerly, false)

    private val _showSideDrawer = MutableStateFlow(false)
    val showSideDrawer: StateFlow<Boolean> = _showSideDrawer.asStateFlow()

    private val _showSettings = MutableStateFlow(false)
    val showSettings: StateFlow<Boolean> = _showSettings.asStateFlow()

    private val _showAgentDropdown = MutableStateFlow(false)
    val showAgentDropdown: StateFlow<Boolean> = _showAgentDropdown.asStateFlow()

    // Selected agent - synced with BackendUrlRepository
    val selectedAgent: StateFlow<AgentInfo> = backendUrlRepository.selectedAgent.map { agentId ->
        AgentInfo.AGENTS.find { it.type.name.equals(agentId, ignoreCase = true) } ?: AgentInfo.AGENTS.first()
    }.stateIn(viewModelScope, SharingStarted.Eagerly, AgentInfo.AGENTS.first())

    // Three-way touch mode: NONE (view only) → TOUCHPAD (relative) → TABLET (absolute) → NONE …
    private val _touchMode = MutableStateFlow(TouchMode.TABLET)
    val touchMode: StateFlow<TouchMode> = _touchMode.asStateFlow()
    val isTouchpadMode: StateFlow<Boolean> = _touchMode
        .map { it == TouchMode.TOUCHPAD }
        .stateIn(viewModelScope, SharingStarted.Eagerly, false)
    val isTabletMode: StateFlow<Boolean> = _touchMode
        .map { it == TouchMode.TABLET }
        .stateIn(viewModelScope, SharingStarted.Eagerly, true)

    fun cycleTouchMode() {
        _touchMode.value = when (_touchMode.value) {
            TouchMode.NONE -> TouchMode.TOUCHPAD
            TouchMode.TOUCHPAD -> TouchMode.TABLET
            TouchMode.TABLET -> TouchMode.NONE
        }
        _localCursor.value = Offset(0.5f, 0.5f)
    }

    // Locally-owned cursor position (normalized, 0..1). Rendered instantly on
    // phone so the arrow is latency-free; PC follows via direct_move events.
    private val _localCursor = MutableStateFlow(Offset(0.5f, 0.5f))
    val localCursor: StateFlow<Offset> = _localCursor.asStateFlow()
    fun setLocalCursor(pos: Offset) { _localCursor.value = pos }

    private val _isScrollMode = MutableStateFlow(false)
    val isScrollMode: StateFlow<Boolean> = _isScrollMode.asStateFlow()

    private val _isClickMode = MutableStateFlow(false)
    val isClickMode: StateFlow<Boolean> = _isClickMode.asStateFlow()

    private val _isFocusMode = MutableStateFlow(false)
    val isFocusMode: StateFlow<Boolean> = _isFocusMode.asStateFlow()

    private val _isKeyboardOpen = MutableStateFlow(false)
    val isKeyboardOpen: StateFlow<Boolean> = _isKeyboardOpen.asStateFlow()

    // OpenClaw screen control
    val isOpenClawActive: StateFlow<Boolean> = openClawService.state.map { it.connected }.stateIn(viewModelScope, SharingStarted.Eagerly, false)

    // Window selector mode
    private val _isWindowSelectorMode = MutableStateFlow(false)
    val isWindowSelectorMode: StateFlow<Boolean> = _isWindowSelectorMode.asStateFlow()

    // Remote PC state
    private val _isScreenMode = MutableStateFlow(false)
    val isScreenMode: StateFlow<Boolean> = _isScreenMode.asStateFlow()

    private val _isFullscreen = MutableStateFlow(false)
    val isFullscreen: StateFlow<Boolean> = _isFullscreen.asStateFlow()

    private val _isScreenConnecting = MutableStateFlow(false)
    val isScreenConnecting: StateFlow<Boolean> = _isScreenConnecting.asStateFlow()

    private val _isDisplaySwitching = MutableStateFlow(false)
    val isDisplaySwitching: StateFlow<Boolean> = _isDisplaySwitching.asStateFlow()

    // Voice typing state
    private val _isVoiceTyping = MutableStateFlow(false)
    val isVoiceTyping: StateFlow<Boolean> = _isVoiceTyping.asStateFlow()

    private val _showVoiceRecording = MutableStateFlow(false)
    val showVoiceRecording: StateFlow<Boolean> = _showVoiceRecording.asStateFlow()

    // Speak (TTS) mode
    private val _isSpeakEnabled = MutableStateFlow(false)
    val isSpeakEnabled: StateFlow<Boolean> = _isSpeakEnabled.asStateFlow()

    private val _isAttachmentMenuOpen = MutableStateFlow(false)
    val isAttachmentMenuOpen: StateFlow<Boolean> = _isAttachmentMenuOpen.asStateFlow()

    private val _showChatHistoryDrawer = MutableStateFlow(false)
    val showChatHistoryDrawer: StateFlow<Boolean> = _showChatHistoryDrawer.asStateFlow()

    private val _isOverlayEnabled = MutableStateFlow(false)
    val isOverlayEnabled: StateFlow<Boolean> = _isOverlayEnabled.asStateFlow()

    // Toolbar position (draggable)
    private val _toolbarOffset = MutableStateFlow(Offset(16f, 200f))
    val toolbarOffset: StateFlow<Offset> = _toolbarOffset.asStateFlow()

    // Auto-play trigger: pair of (messageId, audioUrl)
    private val _autoPlayTrigger = MutableStateFlow<Pair<String, String>?>(null)
    val autoPlayTrigger: StateFlow<Pair<String, String>?> = _autoPlayTrigger.asStateFlow()

    // Currently playing message ID (shared between AudioPlayer and MessageBubble)
    private val _playingMessageId = MutableStateFlow<String?>(null)
    val playingMessageId: StateFlow<String?> = _playingMessageId.asStateFlow()

    fun setPlayingMessage(msgId: String?) {
        _playingMessageId.value = msgId
    }

    // Voice connection state
    val voiceConnectionState: StateFlow<VoiceConnectionState> = voiceService.connectionState

    // LiveKit Video Track
    val videoTrack: StateFlow<VideoTrack?> = liveKitService.videoTrack
    val currentRoom: StateFlow<Room?> = liveKitService.currentRoom

    // Backend health state
    val healthState: StateFlow<BackendHealthState> = backendUrlRepository.healthState
    val backendUrl: String get() = backendUrlRepository.currentUrl.value

    // ----- Multi-tab / Multi-session state -----
    // Map of agent -> list of conversation summaries (from API)
    private val _conversationsByAgent = MutableStateFlow<Map<AgentType, List<ConversationSummary>>>(emptyMap())
    val conversationsByAgent: StateFlow<Map<AgentType, List<ConversationSummary>>> = _conversationsByAgent.asStateFlow()

    // Open tabs per agent (in-memory only)
    private val _openTabs = MutableStateFlow<Map<AgentType, List<Tab>>>(emptyMap())
    val openTabs: StateFlow<Map<AgentType, List<Tab>>> = _openTabs.asStateFlow()

    // Currently active tab CID (for selected agent)
    private val _activeTabCid = MutableStateFlow<String?>(null)
    val activeTabCid: StateFlow<String?> = _activeTabCid.asStateFlow()

    // Messages for the active tab (loaded from API)
    private val _tabMessages = MutableStateFlow<List<Message>>(emptyList())
    val tabMessages: StateFlow<List<Message>> = _tabMessages.asStateFlow()

    private val conversationId = "mobile_${System.currentTimeMillis()}"

    init {
        observeMessages()
        // Wait for backend URL initialization before connecting WebSocket and loading conversations
        viewModelScope.launch {
            startupRepository.isInitialized.collect { initialized ->
                if (initialized) {
                    connectWebSocket()
                    loadConversationsForAgent(selectedAgent.value.type)
                    startHealthCheckLoop()
                    // Start floating overlay by default
                    OverlayService.start(context)
                    _isOverlayEnabled.value = true
                }
            }
        }
    }

    private fun startHealthCheckLoop() {
        viewModelScope.launch {
            while (true) {
                backendUrlRepository.checkHealth()
                kotlinx.coroutines.delay(10000) // Check every 10 seconds
            }
        }
    }

    private fun connectWebSocket() {
        // Legacy - WebSocket is no longer used for chat
        // ChatDataChannelService handles connections in sendMessage()
        android.util.Log.d("ChatDC", "connectWebSocket called - legacy, not used for chat")
    }

    private fun observeMessages() {
        viewModelScope.launch {
            android.util.Log.d("ChatDC", "observeMessages: starting collection")
            chatDataChannelService.messages.collect { msg ->
                android.util.Log.d("ChatDC", "observeMessages: received msg type=${msg.javaClass.simpleName}")
                when (msg) {
                    is ChatMessage.TextMessage -> {
                        android.util.Log.d("ChatDC", "Received text message: ${msg.text.take(50)}, sender=${msg.sender}")
                        // Skip user messages — they are already added locally when the user sends them.
                        if (msg.sender == "user") return@collect
                        val wantVoice = _isSpeakEnabled.value && msg.text.isNotEmpty() && msg.origin != "overlay"
                        val newMsg = Message(
                            id = msg.messageId,
                            text = msg.text,
                            isUser = false,
                            isVoice = wantVoice  // Show voice box immediately if speak is on
                        )
                        _tabMessages.value = _tabMessages.value + newMsg
                        _isLoading.value = false
                        android.util.Log.d("ChatDC", "Updated _tabMessages, count=${_tabMessages.value.size}, isVoice=$wantVoice")

                        if (wantVoice) {
                            generateTts(newMsg.id, msg.text)
                        }
                    }
                    is ChatMessage.VoiceMessage -> {
                        android.util.Log.d("ChatDC", "Received voice message: ${msg.messageId}, sender=${msg.sender}")
                        // Skip user voice messages — already displayed locally as placeholders.
                        // Only render agent voice replies (audio responses) from DataChannel.
                        if (msg.sender == "user") return@collect
                        val newMsg = Message(
                            id = msg.messageId,
                            text = "",
                            isUser = false,
                            isVoice = true,
                            audioUrl = msg.audioUrl
                        )
                        _tabMessages.value = _tabMessages.value + newMsg
                        _isLoading.value = false
                    }
                    is ChatMessage.SystemMessage -> {
                        android.util.Log.d("ChatDC", "Received system message: ${msg.topic}")
                        if (msg.topic == "task.done" || msg.topic == "node.done") {
                            _isLoading.value = false
                        }
                    }
                    else -> {
                        android.util.Log.d("ChatDC", "Received other message type")
                    }
                }
            }
        }
    }

    private fun addMessage(message: Message) {
        _messages.value = _messages.value + message
    }

    fun updateInputText(text: String) {
        _inputText.value = text
    }

    fun sendMessage() {
        val text = _inputText.value.trim()
        if (text.isEmpty()) return

        _inputText.value = ""

        // If no active tab or placeholder tab, create a new conversation first
        val currentCid = _activeTabCid.value
        if (currentCid == null || currentCid.startsWith("new_")) {
            createNewTabAndSend(text)
            return
        }

        val msgId = "user_${UUID.randomUUID()}"
        _tabMessages.value = _tabMessages.value + Message(
            id = msgId,
            text = text,
            isUser = true
        )

        if (_isSpeakEnabled.value) {
            generateTts(msgId, text)
        }

        _isLoading.value = true

        viewModelScope.launch {
            val cid = _activeTabCid.value ?: return@launch

            // Ensure connected to the chat room
            if (!chatDataChannelService.connectionState.value.connected ||
                chatDataChannelService.connectionState.value.conversationId != cid) {
                android.util.Log.d("ChatDC", "Connecting to chat room for cid: $cid")
                val connected = chatDataChannelService.connect(cid)
                if (!connected) {
                    _isLoading.value = false
                    _tabMessages.value = _tabMessages.value + Message(
                        id = "error_${UUID.randomUUID()}",
                        text = "Failed to connect to chat",
                        isUser = false
                    )
                    return@launch
                }
            }

            val success = chatDataChannelService.sendTextMessage(text)
            if (!success) {
                _isLoading.value = false
                _tabMessages.value = _tabMessages.value + Message(
                    id = "error_${UUID.randomUUID()}",
                    text = "Failed to send message",
                    isUser = false
                )
            }
        }

        // Timeout: clear loading if no response after 45s
        viewModelScope.launch {
            kotlinx.coroutines.delay(45_000)
            if (_isLoading.value) {
                android.util.Log.w("ChatDC", "Loading timeout - clearing loading state after 45s")
                _isLoading.value = false
            }
        }
    }

    private fun generateTts(msgId: String, text: String) {
        val cid = _activeTabCid.value ?: run {
            android.util.Log.e("TTS", "generateTts: cid is null, returning early")
            return
        }
        android.util.Log.d("TTS", "generateTts: starting for msgId=$msgId cid=$cid text=${text.take(50)}")
        viewModelScope.launch(kotlinx.coroutines.Dispatchers.IO) {
            try {
                val baseUrl = backendUrlRepository.currentUrl.value
                android.util.Log.d("TTS", "generateTts: baseUrl=$baseUrl")
                val escapedText = text.replace("\\", "\\\\").replace("\"", "\\\"").replace("\n", "\\n")
                val reqBody = """{"text":"$escapedText","cid":"$cid","voice":"alloy","msg_id":"$msgId"}"""
                    .toRequestBody("application/json".toMediaType())
                val request = okhttp3.Request.Builder()
                    .url("$baseUrl/tts")
                    .post(reqBody)
                    .header("ngrok-skip-browser-warning", "true")
                    .build()

                val response = okhttp3.OkHttpClient().newCall(request).execute()
                android.util.Log.d("TTS", "generateTts response code=${response.code}")
                if (!response.isSuccessful) {
                    android.util.Log.d("TTS", "TTS failed: ${response.code}")
                    return@launch
                }
                val body2 = response.body?.string() ?: run {
                    android.util.Log.d("TTS", "TTS response body null")
                    return@launch
                }
                val json = org.json.JSONObject(body2)
                val audioUrl = json.optString("audio_url", "")
                android.util.Log.d("TTS", "audioUrl from server: $audioUrl")
                if (audioUrl.isEmpty()) {
                    android.util.Log.d("TTS", "audioUrl was empty in response")
                    return@launch
                }
                _tabMessages.value = _tabMessages.value.map { msg ->
                    if (msg.id == msgId) {
                        android.util.Log.d("TTS", "Updating msg ${msg.id} with audioUrl=$audioUrl")
                        // Show voice box for agent replies when speak is enabled
                        if (!msg.isUser) msg.copy(audioUrl = audioUrl, isVoice = true)
                        else msg.copy(audioUrl = audioUrl)
                    } else msg
                }
                android.util.Log.d("TTS", "Updated message $msgId with audioUrl")
                if (_isSpeakEnabled.value) {
                    android.util.Log.d("TTS", "Setting autoPlayTrigger for $msgId")
                    _autoPlayTrigger.value = msgId to audioUrl
                } else {
                    android.util.Log.d("TTS", "Speak disabled, skipping autoPlayTrigger")
                }
            } catch (e: Exception) {
                android.util.Log.e("TTS", "Failed to generate TTS: ${e.message}", e)
            }
        }
    }

    private fun createNewTabAndSend(text: String) {
        val agent = selectedAgent.value.type
        // Show message immediately
        val msgId = "user_${UUID.randomUUID()}"
        _tabMessages.value = listOf(Message(id = msgId, text = text, isUser = true))
        _isLoading.value = true

        viewModelScope.launch(kotlinx.coroutines.Dispatchers.IO) {
            try {
                val baseUrl = backendUrlRepository.currentUrl.value
                val agentType = agent.name.lowercase()
                val requestBody = """{"agent_id": "$agentType"}""".toRequestBody("application/json".toMediaType())
                val request = okhttp3.Request.Builder()
                    .url("$baseUrl/conversation")
                    .post(requestBody)
                    .header("ngrok-skip-browser-warning", "true")
                    .build()

                okhttp3.OkHttpClient().newCall(request).execute().use { response ->
                    if (response.isSuccessful) {
                        val body = response.body?.string()
                        val json = org.json.JSONObject(body ?: "{}")
                        val cid = json.getString("cid")

                        // Open the conversation (adds tab, sets active)
                        openConversation(cid)
                        // Restore the optimistic message (openConversation clears tabMessages)
                        _tabMessages.value = listOf(Message(id = msgId, text = text, isUser = true))

                        // Connect and send via DataChannel
                        val connected = chatDataChannelService.connect(cid)
                        if (connected) {
                            val success = chatDataChannelService.sendTextMessage(text)
                            if (!success) {
                                _isLoading.value = false
                                _tabMessages.value = _tabMessages.value + Message(
                                    id = "error_${UUID.randomUUID()}",
                                    text = "Failed to send message",
                                    isUser = false
                                )
                            }
                        } else {
                            _isLoading.value = false
                            _tabMessages.value = _tabMessages.value + Message(
                                id = "error_${UUID.randomUUID()}",
                                text = "Failed to connect to chat",
                                isUser = false
                            )
                        }
                    }
                }
            } catch (e: Exception) {
                android.util.Log.e("ConversationVM", "Failed to create conversation and send", e)
                _isLoading.value = false
            }
        }

        // Loading timeout
        viewModelScope.launch {
            kotlinx.coroutines.delay(45_000)
            if (_isLoading.value) {
                _isLoading.value = false
            }
        }
    }

    fun toggleSideDrawer() {
        _showSideDrawer.value = !_showSideDrawer.value
    }

    fun toggleChatHistoryDrawer() {
        _showChatHistoryDrawer.value = !_showChatHistoryDrawer.value
    }

    fun toggleSettings() {
        _showSettings.value = !_showSettings.value
    }

    fun toggleAgentDropdown() {
        _showAgentDropdown.value = !_showAgentDropdown.value
    }

    fun selectAgent(agent: AgentInfo) {
        viewModelScope.launch {
            backendUrlRepository.setSelectedAgent(agent.type.name.lowercase())
        }
        _showAgentDropdown.value = false
        // Clear active tab and messages when switching agents (show chat list for new agent)
        _activeTabCid.value = null
        _tabMessages.value = emptyList()
        // Load conversations for this agent
        loadConversationsForAgent(agent.type)
    }

    private fun loadConversationsForAgent(agentType: AgentType) {
        viewModelScope.launch(kotlinx.coroutines.Dispatchers.IO) {
            try {
                val baseUrl = backendUrlRepository.currentUrl.value
                val request = okhttp3.Request.Builder()
                    .url("$baseUrl/conversations?agent_id=${agentType.name.lowercase()}")
                    .get()
                    .header("ngrok-skip-browser-warning", "true")
                    .build()

                okhttp3.OkHttpClient().newCall(request).execute().use { response ->
                    if (response.isSuccessful) {
                        val body = response.body?.string()
                        val json = org.json.JSONArray(body ?: "[]")
                        val conversations = mutableListOf<ConversationSummary>()
                        for (i in 0 until json.length()) {
                            val obj = json.getJSONObject(i)
                            conversations.add(ConversationSummary(
                                id = obj.getString("id"),
                                title = obj.optString("title", "New Chat"),
                                lastMessage = obj.optString("lastMessage", ""),
                                updatedAt = obj.optString("updatedAt", ""),
                                agentId = obj.optString("agentId")
                            ))
                        }
                        // Update the map for this agent
                        _conversationsByAgent.value = _conversationsByAgent.value.toMutableMap().apply {
                            put(agentType, conversations)
                        }
                    }
                }
            } catch (e: Exception) {
                android.util.Log.e("ConversationVM", "Failed to load conversations", e)
            }
        }
    }

    fun openConversation(cid: String) {
        // Skip if already on this tab
        if (_activeTabCid.value == cid) return

        val agent = selectedAgent.value.type
        val currentTabs = _openTabs.value.toMutableMap()
        val agentTabs = currentTabs[agent]?.toMutableList() ?: mutableListOf()

        if (agentTabs.none { it.cid == cid }) {
            // Get title from conversations list
            val convList = _conversationsByAgent.value[agent] ?: emptyList()
            val title = convList.find { it.id == cid }?.title ?: "New Chat"
            agentTabs.add(Tab(cid = cid, title = title, isActive = true))
        }

        // Mark only the selected tab as active
        val updatedTabs = agentTabs.map { it.copy(isActive = it.cid == cid) }
        currentTabs[agent] = updatedTabs
        _openTabs.value = currentTabs

        // Set active tab CID
        _activeTabCid.value = cid
        // Clear stale loading state from previous tab
        _isLoading.value = false

        // Only load messages from server for real CIDs (not placeholder tabs)
        if (!cid.startsWith("new_")) {
            loadMessages(cid)
            // Reconnect DataChannel to this conversation's room
            viewModelScope.launch {
                chatDataChannelService.connect(cid)
            }
        } else {
            _isTabLoading.value = false
            _tabMessages.value = emptyList()
        }
    }

    fun closeTab(cid: String) {
        val agent = selectedAgent.value.type
        val currentTabs = _openTabs.value.toMutableMap()
        val agentTabs = currentTabs[agent]?.toMutableList() ?: mutableListOf()

        agentTabs.removeAll { it.cid == cid }
        currentTabs[agent] = agentTabs
        _openTabs.value = currentTabs

        // If we closed the active tab, clear active tab or switch to another
        if (_activeTabCid.value == cid) {
            _activeTabCid.value = agentTabs.firstOrNull()?.cid
            // Load messages for the new active tab or clear if none
            if (_activeTabCid.value != null) {
                loadMessages(_activeTabCid.value!!)
            } else {
                _tabMessages.value = emptyList()
            }
        }
    }

    fun renameConversation(cid: String, newTitle: String) {
        viewModelScope.launch(kotlinx.coroutines.Dispatchers.IO) {
            try {
                val baseUrl = backendUrlRepository.currentUrl.value
                val requestBody = """{"title": "$newTitle"}""".toRequestBody("application/json".toMediaType())
                val request = okhttp3.Request.Builder()
                    .url("$baseUrl/conversation/$cid")
                    .method("PATCH", requestBody)
                    .header("ngrok-skip-browser-warning", "true")
                    .build()

                okhttp3.OkHttpClient().newCall(request).execute().use { response ->
                    if (response.isSuccessful) {
                        // Update local tab title
                        val agent = selectedAgent.value.type
                        val currentTabs = _openTabs.value.toMutableMap()
                        val agentTabs = currentTabs[agent]?.toMutableList() ?: mutableListOf()
                        val index = agentTabs.indexOfFirst { it.cid == cid }
                        if (index >= 0) {
                            agentTabs[index] = agentTabs[index].copy(title = newTitle)
                            currentTabs[agent] = agentTabs
                            _openTabs.value = currentTabs
                        }
                        // Reload conversations list to reflect rename immediately
                        loadConversationsForAgent(agent)
                        Log.d("ConversationVM", "Conversation renamed to: $newTitle")
                    } else {
                        Log.e("ConversationVM", "Failed to rename conversation: ${response.code}")
                    }
                }
            } catch (e: Exception) {
                Log.e("ConversationVM", "Rename conversation failed", e)
            }
        }
    }

    fun createNewTab() {
        val agent = selectedAgent.value.type
        val tempCid = "new_${UUID.randomUUID().toString().take(8)}"

        // Add placeholder tab and activate it
        val currentTabs = _openTabs.value.toMutableMap()
        val agentTabs = (currentTabs[agent] ?: emptyList())
            .map { it.copy(isActive = false) } + Tab(cid = tempCid, title = "New Chat", isActive = true)
        currentTabs[agent] = agentTabs
        _openTabs.value = currentTabs
        _activeTabCid.value = tempCid
        _tabMessages.value = emptyList()
        _isLoading.value = false

        // Background: create on server and swap CID (only if user is still on this tab)
        viewModelScope.launch(kotlinx.coroutines.Dispatchers.IO) {
            try {
                val baseUrl = backendUrlRepository.currentUrl.value
                val agentType = agent.name.lowercase()
                val requestBody = """{"agent_id": "$agentType"}""".toRequestBody("application/json".toMediaType())
                val request = okhttp3.Request.Builder()
                    .url("$baseUrl/conversation")
                    .post(requestBody)
                    .header("ngrok-skip-browser-warning", "true")
                    .build()

                okhttp3.OkHttpClient().newCall(request).execute().use { response ->
                    if (response.isSuccessful) {
                        val body = response.body?.string()
                        val json = org.json.JSONObject(body ?: "{}")
                        val realCid = json.getString("cid")

                        // Swap placeholder CID in tab list
                        val tabs = _openTabs.value.toMutableMap()
                        val list = tabs[agent]?.toMutableList() ?: mutableListOf()
                        val idx = list.indexOfFirst { it.cid == tempCid }
                        if (idx >= 0) {
                            // Preserve whatever isActive state the tab currently has
                            list[idx] = list[idx].copy(cid = realCid)
                            tabs[agent] = list
                            _openTabs.value = tabs
                        }
                        // Only update activeTabCid if user hasn't switched away
                        if (_activeTabCid.value == tempCid) {
                            _activeTabCid.value = realCid
                        }
                    }
                }
            } catch (e: Exception) {
                android.util.Log.e("ConversationVM", "Failed to create conversation", e)
            }
        }
    }

    fun deleteConversation(cid: String) {
        viewModelScope.launch(kotlinx.coroutines.Dispatchers.IO) {
            try {
                val baseUrl = backendUrlRepository.currentUrl.value
                val request = okhttp3.Request.Builder()
                    .url("$baseUrl/conversation/$cid")
                    .delete()
                    .header("ngrok-skip-browser-warning", "true")
                    .build()

                okhttp3.OkHttpClient().newCall(request).execute().use { response ->
                    if (response.isSuccessful) {
                        // Remove from open tabs if present
                        val agent = selectedAgent.value.type
                        val currentTabs = _openTabs.value.toMutableMap()
                        val agentTabs = currentTabs[agent]?.toMutableList() ?: mutableListOf()
                        agentTabs.removeAll { it.cid == cid }
                        currentTabs[agent] = agentTabs
                        _openTabs.value = currentTabs

                        // Clear active tab if it was the deleted one
                        if (_activeTabCid.value == cid) {
                            _activeTabCid.value = agentTabs.firstOrNull()?.cid
                        }

                        // Reload conversations list
                        loadConversationsForAgent(agent)
                        Log.d("ConversationVM", "Conversation deleted: $cid")
                    } else {
                        Log.e("ConversationVM", "Failed to delete conversation: ${response.code}")
                    }
                }
            } catch (e: Exception) {
                Log.e("ConversationVM", "Delete conversation failed", e)
            }
        }
    }

    private fun loadMessages(cid: String) {
        _isTabLoading.value = true
        viewModelScope.launch(kotlinx.coroutines.Dispatchers.IO) {
            try {
                val baseUrl = backendUrlRepository.currentUrl.value
                val request = okhttp3.Request.Builder()
                    .url("$baseUrl/conversation/$cid")
                    .get()
                    .header("ngrok-skip-browser-warning", "true")
                    .build()

                okhttp3.OkHttpClient().newCall(request).execute().use { response ->
                    if (response.isSuccessful) {
                        val body = response.body?.string()
                        val json = org.json.JSONObject(body ?: "{}")
                        val messagesArray = json.getJSONArray("messages")
                        val msgs = mutableListOf<Message>()
                        for (i in 0 until messagesArray.length()) {
                            val msgObj = messagesArray.getJSONObject(i)
                            val rawAudioUrl = if (msgObj.isNull("audioUrl")) null else msgObj.optString("audioUrl", "").takeIf { it.isNotEmpty() && it != "null" }
                            val isVoice = msgObj.optBoolean("isVoice", false) || rawAudioUrl != null
                            android.util.Log.d("LoadMsgs", "Msg[$i]: role=${msgObj.optString("role")}, isVoice=$isVoice, audioUrl=$rawAudioUrl, content=${msgObj.optString("content").take(30)}")
                            msgs.add(Message(
                                id = msgObj.optString("id", "${i}"),
                                text = msgObj.optString("content", ""),
                                isUser = msgObj.optString("role") == "user",
                                isVoice = isVoice,
                                audioUrl = rawAudioUrl
                            ))
                        }
                        _tabMessages.value = msgs
                    }
                }
            } catch (e: Exception) {
                android.util.Log.e("ConversationVM", "Failed to load messages", e)
            } finally {
                _isTabLoading.value = false
            }
        }
    }

    fun exitTouchMode() {
        if (_touchMode.value != TouchMode.NONE) {
            _touchMode.value = TouchMode.NONE
        }
    }

    fun toggleWindowSelectorMode() {
        _isWindowSelectorMode.value = !_isWindowSelectorMode.value
    }

    fun toggleScrollMode() {
        _isScrollMode.value = !_isScrollMode.value
    }

    fun toggleClickMode() {
        _isClickMode.value = !_isClickMode.value
    }

    fun toggleFocusMode() {
        _isFocusMode.value = !_isFocusMode.value
    }

    fun toggleKeyboard() {
        _isKeyboardOpen.value = !_isKeyboardOpen.value
    }


    fun toggleOpenClaw() {
        viewModelScope.launch {
            val currentlyConnected = openClawService.state.value.connected
            if (currentlyConnected) {
                openClawService.disconnect()
            } else {
                openClawService.connect()
            }
        }
    }

    fun toggleScreenShare() {
        viewModelScope.launch {
            if (_isScreenMode.value) {
                // Turn off screen mode
                liveKitService.sendSession("mobile_disconnect")
                orientationService.stop()
                liveKitService.disconnect()
                _isScreenMode.value = false
                _isFullscreen.value = false
                android.util.Log.d("NeuroMobile", "[Screen] Disconnected")
            } else {
                // Start screen mode
                _isScreenConnecting.value = true
                android.util.Log.d("NeuroMobile", "[Screen] Starting screen share...")
                try {
                    val userId = "mobile_${System.currentTimeMillis()}"
                    
                    // Get voice token (runs on IO thread)
                    val tokenResult = kotlinx.coroutines.withContext(kotlinx.coroutines.Dispatchers.IO) {
                        voiceService.getVoiceToken(userId)
                    }
                    
                    tokenResult.onSuccess { voiceToken ->
                        android.util.Log.d("NeuroMobile", "[Screen] Got token. URL: ${voiceToken.url}, Room: ${voiceToken.roomName}")
                        
                        // Rewrite LiveKit URL if it's localhost (phone can't reach localhost)
                        var resolvedUrl = voiceToken.url
                        if (resolvedUrl.contains("127.0.0.1") || resolvedUrl.contains("localhost")) {
                            val baseUrl = backendUrlRepository.currentUrl.value
                            val hostMatch = Regex("https?://([^:/]+)").find(baseUrl)
                            if (hostMatch != null) {
                                val apiHost = hostMatch.groupValues[1]
                                resolvedUrl = resolvedUrl
                                    .replace("127.0.0.1", apiHost)
                                    .replace("localhost", apiHost)
                                android.util.Log.d("NeuroMobile", "[Screen] Rewrote LiveKit URL to: $resolvedUrl")
                            }
                        }
                        
                        // Call /screen/start on backend (runs on IO thread)
                        kotlinx.coroutines.withContext(kotlinx.coroutines.Dispatchers.IO) {
                            try {
                                val baseUrl = backendUrlRepository.currentUrl.value
                                val requestBody = """{"user_id":"$userId"}"""
                                val request = okhttp3.Request.Builder()
                                    .url("$baseUrl/screen/start")
                                    .post(requestBody.toRequestBody("application/json".toMediaType()))
                                    .header("ngrok-skip-browser-warning", "true")
                                    .build()
                                okhttp3.OkHttpClient().newCall(request).execute().close()
                                android.util.Log.d("NeuroMobile", "[Screen] /screen/start called successfully")
                            } catch (e: Exception) {
                                android.util.Log.e("NeuroMobile", "[Screen] Failed to start screen: ${e.message}")
                            }
                        }

                        val success = liveKitService.connect(
                            token = voiceToken.token,
                            url = resolvedUrl,
                            roomName = voiceToken.roomName
                        )
                        android.util.Log.d("NeuroMobile", "[Screen] LiveKit connect result: $success")
                        _isScreenMode.value = success
                        if (success) {
                            // Always go full-screen immediately; the small-
                            // window-over-chat variant is retired.
                            _isFullscreen.value = true
                            liveKitService.sendSession("mobile_connect")
                            // Orientation syncing only runs when the user has
                            // opted in via Settings → "Rotate desktop display".
                            if (backendUrlRepository.rotateDesktop.value) {
                                orientationService.start { state, locked ->
                                    liveKitService.sendOrientation(state.wire, locked)
                                }
                                // LiveKit's data channel isn't usable the
                                // instant room.connect returns — SCTP
                                // negotiation takes a couple seconds. Resend
                                // the current orientation at 1s, 2s, 4s so
                                // at least one lands on the server once its
                                // data handler is receiving. Server-side
                                // dedup ignores duplicates.
                                viewModelScope.launch {
                                    for (ms in listOf(1000L, 2000L, 4000L)) {
                                        kotlinx.coroutines.delay(ms)
                                        orientationService.resendLast()
                                    }
                                }
                            }
                        }
                    }
                    tokenResult.onFailure { error ->
                        android.util.Log.e("NeuroMobile", "[Screen] Failed to get token: ${error.message}")
                        _isScreenMode.value = false
                    }
                } catch (e: Exception) {
                    android.util.Log.e("NeuroMobile", "[Screen] Error: ${e.message}", e)
                } finally {
                    _isScreenConnecting.value = false
                }
            }
        }
    }

    // MediaRecorder setup for voice typing — streams audio in ~10s chunks
    private var mediaRecorder: android.media.MediaRecorder? = null
    private var voiceFile: java.io.File? = null
    private var chunkTimer: java.util.Timer? = null
    private val voiceTypeClient = okhttp3.OkHttpClient.Builder()
        .connectTimeout(30, java.util.concurrent.TimeUnit.SECONDS)
        .readTimeout(60, java.util.concurrent.TimeUnit.SECONDS)
        .writeTimeout(30, java.util.concurrent.TimeUnit.SECONDS)
        .build()

    fun toggleVoiceTyping() {
        if (_isVoiceTyping.value) {
            submitVoiceType(false)
        } else {
            startVoiceRecording()
        }
    }

    private fun startVoiceRecording() {
        try {
            val permCheck = android.content.pm.PackageManager.PERMISSION_GRANTED ==
                androidx.core.content.ContextCompat.checkSelfPermission(
                    context, android.Manifest.permission.RECORD_AUDIO
                )
            if (!permCheck) {
                android.util.Log.e("VoiceType", "RECORD_AUDIO permission not granted!")
                _isVoiceTyping.value = false
                return
            }

            startNewRecorderChunk()
            _isVoiceTyping.value = true

            // Start chunk timer — every 10 seconds, flush current chunk and send it
            chunkTimer = java.util.Timer()
            chunkTimer?.schedule(object : java.util.TimerTask() {
                override fun run() {
                    flushAndSendChunk()
                }
            }, 10000L, 10000L)

            android.util.Log.d("VoiceType", "Recording started with 10s chunking")
        } catch (e: Exception) {
            android.util.Log.e("VoiceType", "Failed to start recording: ${e.message}", e)
            _isVoiceTyping.value = false
        }
    }

    private fun startNewRecorderChunk() {
        voiceFile = java.io.File(context.cacheDir, "voice_type_${System.currentTimeMillis()}.m4a")
        android.util.Log.d("VoiceType", "New chunk: ${voiceFile?.absolutePath}")
        mediaRecorder = android.media.MediaRecorder().apply {
            setAudioSource(android.media.MediaRecorder.AudioSource.MIC)
            setOutputFormat(android.media.MediaRecorder.OutputFormat.MPEG_4)
            setAudioEncoder(android.media.MediaRecorder.AudioEncoder.AAC)
            setOutputFile(voiceFile?.absolutePath)
            prepare()
            start()
        }
    }

    @Synchronized
    private fun flushAndSendChunk() {
        try {
            val finishedFile = voiceFile
            val recorder = mediaRecorder

            // Stop current recorder
            recorder?.stop()
            recorder?.release()
            mediaRecorder = null

            // Start a new recorder immediately to minimize gap
            if (_isVoiceTyping.value) {
                startNewRecorderChunk()
            }

            // Upload the finished chunk (no press_enter for intermediate chunks)
            finishedFile?.let { uploadVoiceChunk(it, pressEnter = false) }
        } catch (e: Exception) {
            android.util.Log.e("VoiceType", "Chunk flush failed: ${e.message}", e)
            // Try to restart recorder if still in voice typing mode
            if (_isVoiceTyping.value) {
                try { startNewRecorderChunk() } catch (_: Exception) {}
            }
        }
    }

    private fun uploadVoiceChunk(file: java.io.File, pressEnter: Boolean) {
        viewModelScope.launch(kotlinx.coroutines.Dispatchers.IO) {
            try {
                if (!file.exists() || file.length() == 0L) return@launch
                val baseUrl = backendUrlRepository.currentUrl.value
                val endpoint = if (pressEnter) "$baseUrl/voice-type?press_enter=true" else "$baseUrl/voice-type"
                android.util.Log.d("VoiceType", "Uploading chunk ${file.length()} bytes to $endpoint")

                val requestBody = okhttp3.MultipartBody.Builder()
                    .setType(okhttp3.MultipartBody.FORM)
                    .addFormDataPart("file", file.name, file.readBytes().toRequestBody("audio/m4a".toMediaType()))
                    .build()

                val request = okhttp3.Request.Builder()
                    .url(endpoint)
                    .post(requestBody)
                    .header("ngrok-skip-browser-warning", "true")
                    .build()

                voiceTypeClient.newCall(request).execute().use { response ->
                    val body = response.body?.string()
                    android.util.Log.d("VoiceType", "Chunk response ${response.code}: $body")
                }
            } catch (e: Exception) {
                android.util.Log.e("VoiceType", "Chunk upload failed: ${e.message}", e)
            } finally {
                try { file.delete() } catch (_: Exception) {}
            }
        }
    }

    fun submitVoiceType(pressEnter: Boolean = true) {
        if (!_isVoiceTyping.value) return
        android.util.Log.d("VoiceType", "Submitting final voice type chunk (pressEnter=$pressEnter)")

        // Stop the chunk timer
        chunkTimer?.cancel()
        chunkTimer = null

        try {
            val finalFile = voiceFile
            mediaRecorder?.stop()
            mediaRecorder?.release()
            mediaRecorder = null
            _isVoiceTyping.value = false

            // Upload the final chunk
            finalFile?.let { uploadVoiceChunk(it, pressEnter = pressEnter) }
        } catch (e: Exception) {
            android.util.Log.e("VoiceType", "Submit failed: ${e.message}", e)
            _isVoiceTyping.value = false
        }
    }

    fun cancelVoiceRecording() {
        chunkTimer?.cancel()
        chunkTimer = null
        try {
            mediaRecorder?.stop()
            mediaRecorder?.release()
            mediaRecorder = null
            _isVoiceTyping.value = false
        } catch (e: Exception) {
            e.printStackTrace()
            _isVoiceTyping.value = false
        }
    }

    fun submitVoiceMessage() {
        if (!_isVoiceTyping.value) return
        val file = voiceFile
        if (file == null || !file.exists()) {
            _isVoiceTyping.value = false
            return
        }

        try {
            mediaRecorder?.stop()
            mediaRecorder?.release()
            mediaRecorder = null
            _isVoiceTyping.value = false
        } catch (e: Exception) {
            android.util.Log.e("VoiceMsg", "Failed to stop recorder: ${e.message}", e)
            _isVoiceTyping.value = false
            return
        }

        val existingCid = _activeTabCid.value
        if (existingCid == null) {
            createNewTabAndSendVoice(file)
            return
        }

        uploadAndPollVoiceMessage(file, existingCid)
    }

    private fun uploadAndPollVoiceMessage(file: java.io.File, cid: String) {
        val placeholderId = "voice_${UUID.randomUUID()}"
        _tabMessages.value = _tabMessages.value + Message(
            id = placeholderId,
            text = "(Transcribing...)",
            isUser = true,
            isVoice = true
        )
        _isLoading.value = true

        viewModelScope.launch(kotlinx.coroutines.Dispatchers.IO) {
            // Ensure DataChannel is connected so we receive the agent response
            if (!chatDataChannelService.connectionState.value.connected ||
                chatDataChannelService.connectionState.value.conversationId != cid) {
                val connected = chatDataChannelService.connect(cid)
                if (!connected) {
                    android.util.Log.w("VoiceMsg", "DataChannel not connected, response may be missed")
                }
            }

            val baseUrl = backendUrlRepository.currentUrl.value
            val requestBody = okhttp3.MultipartBody.Builder()
                .setType(okhttp3.MultipartBody.FORM)
                .addFormDataPart("file", file.name, file.readBytes().toRequestBody("audio/m4a".toMediaType()))
                .addFormDataPart("cid", cid)
                .build()

            val request = okhttp3.Request.Builder()
                .url("$baseUrl/voice-message")
                .post(requestBody)
                .header("ngrok-skip-browser-warning", "true")
                .build()

            try {
                okhttp3.OkHttpClient().newCall(request).execute().use { response ->
                    val body = response.body?.string()
                    android.util.Log.d("VoiceMsg", "Upload response ${response.code}: $body")

                    if (response.isSuccessful && body != null) {
                        val json = org.json.JSONObject(body)
                        val transcription = json.optString("transcription", "")
                        val audioUrl = json.optString("audio_url", "").takeIf { it.isNotEmpty() }

                        // Replace placeholder with transcription + audio URL
                        _tabMessages.value = _tabMessages.value.map { msg ->
                            if (msg.id == placeholderId) msg.copy(
                                text = transcription.ifEmpty { "(No transcription)" },
                                isVoice = true,
                                audioUrl = audioUrl
                            ) else msg
                        }
                        // Agent response will arrive via DataChannel → observeMessages
                    } else {
                        _tabMessages.value = _tabMessages.value.map { msg ->
                            if (msg.id == placeholderId) msg.copy(text = "(Transcription failed)") else msg
                        }
                        _isLoading.value = false
                    }
                }
            } catch (e: Exception) {
                android.util.Log.e("VoiceMsg", "Upload failed: ${e.message}", e)
                _tabMessages.value = _tabMessages.value.map { msg ->
                    if (msg.id == placeholderId) msg.copy(text = "(Upload failed)") else msg
                }
                _isLoading.value = false
            }
        }

        // Timeout: clear loading if no response after 45s
        viewModelScope.launch {
            kotlinx.coroutines.delay(45_000)
            if (_isLoading.value) {
                android.util.Log.w("VoiceMsg", "Loading timeout after 45s")
                _isLoading.value = false
            }
        }
    }

    private fun createNewTabAndSendVoice(file: java.io.File) {
        viewModelScope.launch(kotlinx.coroutines.Dispatchers.IO) {
            try {
                val baseUrl = backendUrlRepository.currentUrl.value
                val agentType = selectedAgent.value.type.name.lowercase()
                val requestBody = """{"agent_id": "$agentType"}""".toRequestBody("application/json".toMediaType())
                val request = okhttp3.Request.Builder()
                    .url("$baseUrl/conversation")
                    .post(requestBody)
                    .header("ngrok-skip-browser-warning", "true")
                    .build()

                okhttp3.OkHttpClient().newCall(request).execute().use { response ->
                    if (response.isSuccessful) {
                        val body = response.body?.string()
                        val json = org.json.JSONObject(body ?: "{}")
                        val cid = json.getString("cid")
                        openConversation(cid)

                        uploadAndPollVoiceMessage(file, cid)
                    } else {
                        _tabMessages.value = _tabMessages.value.map { msg ->
                            if (msg.isVoice && msg.isUser && msg.text == "(Transcribing...)") {
                                msg.copy(text = "(Failed to create conversation)")
                            } else msg
                        }
                        _isLoading.value = false
                    }
                }
            } catch (e: Exception) {
                android.util.Log.e("VoiceMsg", "Failed to create conversation: ${e.message}", e)
            }
        }
    }

    fun switchDisplay() {
        _isDisplaySwitching.value = true
        viewModelScope.launch(kotlinx.coroutines.Dispatchers.IO) {
            val baseUrl = backendUrlRepository.currentUrl.value
            val request = okhttp3.Request.Builder()
                .url("$baseUrl/screen/switch-display")
                .post(ByteArray(0).toRequestBody(null))
                .header("ngrok-skip-browser-warning", "true")
                .build()

            try {
                okhttp3.OkHttpClient().newCall(request).execute().close()
                // Give the stream a moment to switch
                kotlinx.coroutines.delay(1200)
            } catch (e: Exception) {
                e.printStackTrace()
            } finally {
                _isDisplaySwitching.value = false
            }
        }
    }

    fun toggleFullscreen() {
        // While screen-share is active the view is always fullscreen — the
        // small-window-over-chat variant is retired. Toggle only outside
        // screen mode.
        if (_isScreenMode.value) return
        _isFullscreen.value = !_isFullscreen.value
    }

    fun toggleOverlay() {
        if (_isOverlayEnabled.value) {
            OverlayService.stop(context)
            _isOverlayEnabled.value = false
        } else {
            if (android.provider.Settings.canDrawOverlays(context)) {
                OverlayService.start(context)
                _isOverlayEnabled.value = true
            } else {
                // Request permission
                val intent = Intent(
                    android.provider.Settings.ACTION_MANAGE_OVERLAY_PERMISSION,
                    android.net.Uri.parse("package:${context.packageName}")
                ).apply {
                    addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                }
                context.startActivity(intent)
            }
        }
    }

    fun reconnectWebSocket(cid: String) {
        // Legacy - WebSocket is no longer used for chat
        // ChatDataChannelService handles connections via connect(cid) in sendMessage()
        android.util.Log.d("ChatDC", "reconnectWebSocket called with cid: $cid - legacy, not used for chat")
        viewModelScope.launch {
            chatDataChannelService.connect(cid)
        }
    }

    fun toggleVoiceRecording() {
        if (_showVoiceRecording.value) {
            _showVoiceRecording.value = false
            cancelVoiceRecording()
        } else {
            startVoiceRecording()
            _showVoiceRecording.value = true
        }
    }

    fun toggleAttachmentMenu() {
        _isAttachmentMenuOpen.value = !_isAttachmentMenuOpen.value
    }

    fun toggleSpeak() {
        _isSpeakEnabled.value = !_isSpeakEnabled.value
    }

    fun updateToolbarOffset(offset: Offset) {
        _toolbarOffset.value = offset
    }

    fun sendKey(key: String) {
        liveKitService.sendKeyEvent(key)
    }

    fun sendMouseMove(dx: Float, dy: Float) {
        liveKitService.sendMouseMove(dx, dy)
    }

    fun sendMouseClick(x: Float, y: Float, button: String = "left") {
        liveKitService.sendMouseClick(x, y, button)
    }

    fun sendMouseDown() {
        liveKitService.sendAction("mousedown")
    }

    fun sendMouseUp() {
        liveKitService.sendAction("mouseup")
    }

    fun sendMouseScroll(dx: Float, dy: Float) {
        liveKitService.sendMouseScroll(dx, dy)
    }

    fun sendDirectMove(x: Float, y: Float) {
        liveKitService.sendDirectMove(x, y)
    }

    fun sendDirectClick(x: Float, y: Float, button: String = "left", count: Int = 1) {
        liveKitService.sendDirectClick(x, y, button, count)
    }

    override fun onCleared() {
        super.onCleared()
        webSocketService.disconnect()
        mediaRecorder?.release()
        mediaRecorder = null
    }
}

/**
 * Returns the rendered video rectangle (offset + size) inside a [containerW]×[containerH]
 * box when the source has aspect ratio [pcW]/[pcH] and is scaled with FitInside.
 * Returns Triple(offsetX, offsetY, renderW, renderH) — all in the same pixel units.
 */
private fun videoRenderRect(
    containerW: Float, containerH: Float,
    pcW: Int, pcH: Int
): FloatArray {
    val pcAspect = if (pcH > 0) pcW.toFloat() / pcH.toFloat() else 16f / 9f
    val phoneAspect = if (containerH > 0) containerW / containerH else 9f / 16f
    val renderW: Float
    val renderH: Float
    if (phoneAspect > pcAspect) {
        // Phone wider → pillarbox (black left/right)
        renderH = containerH
        renderW = containerH * pcAspect
    } else {
        // Phone taller (or equal) → letterbox (black top/bottom)
        renderW = containerW
        renderH = containerW / pcAspect
    }
    return floatArrayOf(
        (containerW - renderW) / 2f,  // offsetX
        (containerH - renderH) / 2f,  // offsetY
        renderW,
        renderH
    )
}

/**
 * Draws a classic OS cursor arrow at PC-normalized [cursorPos] (0..1) mapped
 * precisely into the FitInside video render area within the phone screen.
 */
@Composable
fun CursorArrowOverlay(
    cursorPos: androidx.compose.ui.geometry.Offset?,
    pcScreenWidth: Int = 1920,
    pcScreenHeight: Int = 1080,
    modifier: Modifier = Modifier
) {
    if (cursorPos == null) return
    val density = androidx.compose.ui.platform.LocalDensity.current
    val arrowPx = with(density) { 20.dp.toPx() }
    androidx.compose.foundation.Canvas(modifier = modifier.fillMaxSize()) {
        val vr = videoRenderRect(size.width, size.height, pcScreenWidth, pcScreenHeight)
        val ox = vr[0]; val oy = vr[1]; val rw = vr[2]; val rh = vr[3]
        // Map PC-normalized cursor into the actual video render area
        val px = ox + cursorPos.x * rw
        val py = oy + cursorPos.y * rh
        val s = arrowPx
        // Classic arrow pointer shape (top-left hot-spot)
        val path = androidx.compose.ui.graphics.Path().apply {
            moveTo(px, py)                               // tip
            lineTo(px, py + s)                           // bottom-left
            lineTo(px + s * 0.3f, py + s * 0.62f)       // inner notch left
            lineTo(px + s * 0.54f, py + s * 0.98f)      // right tail bottom
            lineTo(px + s * 0.7f, py + s * 0.88f)       // right tail top
            lineTo(px + s * 0.46f, py + s * 0.56f)      // inner notch right
            lineTo(px + s * 0.78f, py + s * 0.44f)      // right edge
            close()
        }
        // White fill
        drawPath(path, color = Color.White)
        // Black outline
        drawPath(path, color = Color.Black,
            style = androidx.compose.ui.graphics.drawscope.Stroke(width = 2.5f))
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ConversationScreen(
    viewModel: ConversationViewModel = hiltViewModel()
) {
    val messages by viewModel.messages.collectAsState()
    val inputText by viewModel.inputText.collectAsState()
    val isLoading by viewModel.isLoading.collectAsState()
    val isTabLoading by viewModel.isTabLoading.collectAsState()
    val isConnected by viewModel.isConnected.collectAsState()
    val showSideDrawer by viewModel.showSideDrawer.collectAsState()
    val showChatHistoryDrawer by viewModel.showChatHistoryDrawer.collectAsState()
    val showSettings by viewModel.showSettings.collectAsState()
    val showAgentDropdown by viewModel.showAgentDropdown.collectAsState()
    val selectedAgent by viewModel.selectedAgent.collectAsState()
    val isTouchpadMode by viewModel.isTouchpadMode.collectAsState()
    val isScrollMode by viewModel.isScrollMode.collectAsState()
    val isClickMode by viewModel.isClickMode.collectAsState()
    val isFocusMode by viewModel.isFocusMode.collectAsState()
    val isKeyboardOpen by viewModel.isKeyboardOpen.collectAsState()
    val isVoiceTyping by viewModel.isVoiceTyping.collectAsState()
    val showVoiceRecording by viewModel.showVoiceRecording.collectAsState()
    val isSpeakEnabled by viewModel.isSpeakEnabled.collectAsState()
    val isAttachmentMenuOpen by viewModel.isAttachmentMenuOpen.collectAsState()
    val toolbarOffset by viewModel.toolbarOffset.collectAsState()
    val voiceConnectionState by viewModel.voiceConnectionState.collectAsState()
    val healthState by viewModel.healthState.collectAsState()
    val isOpenClawActive by viewModel.isOpenClawActive.collectAsState()
    val isScreenMode by viewModel.isScreenMode.collectAsState()
    val isFullscreen by viewModel.isFullscreen.collectAsState()
    val isScreenConnecting by viewModel.isScreenConnecting.collectAsState()
    val isDisplaySwitching by viewModel.isDisplaySwitching.collectAsState()
    val isWindowSelectorMode by viewModel.isWindowSelectorMode.collectAsState()
    val videoTrack by viewModel.videoTrack.collectAsState()
    val room by viewModel.currentRoom.collectAsState()

    // Multi-tab state
    val conversationsByAgent by viewModel.conversationsByAgent.collectAsState()
    val openTabs by viewModel.openTabs.collectAsState()
    val activeTabCid by viewModel.activeTabCid.collectAsState()
    val tabMessages by viewModel.tabMessages.collectAsState()

    LaunchedEffect(activeTabCid) {
        activeTabCid?.let { cid ->
            viewModel.reconnectWebSocket(cid)
        }
    }

    val listState = rememberLazyListState()
    val context = LocalContext.current

    // Runtime permission for RECORD_AUDIO
    val micPermissionLauncher = rememberLauncherForActivityResult(
        contract = androidx.activity.result.contract.ActivityResultContracts.RequestPermission()
    ) { granted ->
        if (granted) {
            viewModel.toggleVoiceTyping()
        }
    }

    // Push the current display rotation into OrientationService whenever the
    // Activity configuration changes (true OS orientation flip — not sensor
    // noise). Also fires once when screen mode turns on to send initial state.
    val configuration = androidx.compose.ui.platform.LocalConfiguration.current
    LaunchedEffect(isScreenMode, configuration) {
        if (!isScreenMode) return@LaunchedEffect
        val activity = context as? Activity ?: return@LaunchedEffect
        @Suppress("DEPRECATION")
        val rotation = activity.windowManager?.defaultDisplay?.rotation ?: return@LaunchedEffect
        viewModel.onScreenRotationChanged(rotation)
    }

    // Handle immersive mode for fullscreen. Orientation is left to the sensor
    // so that tablet-mode can flip portrait/landscape naturally with the phone.
    DisposableEffect(isFullscreen) {
        val activity = context as? Activity
        val window = activity?.window
        if (window != null) {
            val controller = WindowCompat.getInsetsController(window, window.decorView)
            activity?.requestedOrientation = ActivityInfo.SCREEN_ORIENTATION_FULL_SENSOR
            if (isFullscreen) {
                controller.hide(WindowInsetsCompat.Type.systemBars())
                controller.systemBarsBehavior = WindowInsetsControllerCompat.BEHAVIOR_SHOW_TRANSIENT_BARS_BY_SWIPE
            } else {
                controller.show(WindowInsetsCompat.Type.systemBars())
            }
        }
        onDispose {
            val activity = context as? Activity
            val window = activity?.window
            if (window != null) {
                val controller = WindowCompat.getInsetsController(window, window.decorView)
                activity?.requestedOrientation = ActivityInfo.SCREEN_ORIENTATION_UNSPECIFIED
                controller.show(WindowInsetsCompat.Type.systemBars())
            }
        }
    }

    // Auto-scroll for tab messages (multi-tab chat)
    LaunchedEffect(tabMessages.size) {
        if (tabMessages.isNotEmpty()) {
            listState.animateScrollToItem(tabMessages.size - 1)
        }
    }

    // Audio player for auto-play (outside LazyColumn so not recycled)
    AudioPlayer(
        autoPlayTrigger = viewModel.autoPlayTrigger,
        backendUrl = viewModel.backendUrl,
        onPlayingChanged = { viewModel.setPlayingMessage(it) }
    )

    Box(modifier = Modifier.fillMaxSize()) {
        // Fullscreen remote video track - behind everything else
        if (isFullscreen && isScreenMode) {
            val infiniteTransition = rememberInfiniteTransition()
            val borderColor by infiniteTransition.animateColor(
                initialValue = if (isTouchpadMode) Color(0xFF8BE9FD.toInt()).copy(alpha = 0.3f) else NeuroColors.Primary.copy(alpha = 0.2f),
                targetValue = if (isTouchpadMode) Color(0xFF8BE9FD.toInt()).copy(alpha = 0.9f) else NeuroColors.Primary.copy(alpha = 0.8f),
                animationSpec = infiniteRepeatable(
                    animation = tween(1500, easing = LinearEasing),
                    repeatMode = RepeatMode.Reverse
                ),
                label = "borderPulse"
            )

            // Outer container: fills whole screen, centers the video
            Box(
                modifier = Modifier
                    .fillMaxSize()
                    .background(Color.Black),
                contentAlignment = Alignment.Center
            ) {
                // Inner container: always full-screen — let the VideoTrackView
                // fit the incoming frame aspect inside with letterbox as needed.
                // Orientation follows the device so portrait phone renders a
                // portrait viewport + landscape phone renders landscape.
                Box(
                    modifier = Modifier
                        .fillMaxSize()
                        .border(1.dp, borderColor)
                ) {
                    videoTrack?.let { track ->
                        room?.let { r ->
                            CompositionLocalProvider(RoomLocal provides r) {
                                VideoTrackView(
                                    videoTrack = track,
                                    modifier = Modifier.fillMaxSize(),
                                    scaleType = ScaleType.FitInside
                                )
                            }
                        }
                    }
                    // Transparent gesture layer — tablet mode wins when both flags set.
                    val isTabletMode by viewModel.isTabletMode.collectAsState()
                    val localCursor by viewModel.localCursor.collectAsState()
                    val pcDims by viewModel.remoteScreenDims.collectAsState()
                    if (isTabletMode && !isTouchpadMode) {
                        TabletTouchOverlay(
                            liveKitService = viewModel.liveKitServicePublic,
                            pcScreenWidth = pcDims.first,
                            pcScreenHeight = pcDims.second,
                            onLocalCursorChange = { viewModel.setLocalCursor(it) },
                        )
                    } else if (isTouchpadMode) {
                        TouchpadOverlay(
                            isScrollMode = isScrollMode,
                            isClickMode = isClickMode,
                            isFocusMode = isFocusMode,
                            localCursor = localCursor,
                            pcScreenWidth = pcDims.first,
                            pcScreenHeight = pcDims.second,
                            onExit = { viewModel.exitTouchMode() },
                            onLocalCursorChange = { viewModel.setLocalCursor(it) },
                            onDirectMove = { x, y -> viewModel.sendDirectMove(x, y) },
                            onDirectClick = { x, y, btn, cnt -> viewModel.sendDirectClick(x, y, btn, cnt) },
                            onMouseScroll = { dx, dy -> viewModel.sendMouseScroll(dx, dy) },
                            onMouseDown = { viewModel.sendMouseDown() },
                            onMouseUp = { viewModel.sendMouseUp() },
                        )
                    }

                    // Cursor arrow — local (zero-latency) in touch modes, remote otherwise.
                    val remoteCursor by viewModel.remoteCursorPosition.collectAsState()
                    val arrowPos: Offset? = when {
                        isTouchpadMode || isTabletMode -> localCursor
                        else -> remoteCursor
                    }
                    CursorArrowOverlay(
                        cursorPos = arrowPos,
                        pcScreenWidth = pcDims.first,
                        pcScreenHeight = pcDims.second,
                    )

                    // Window selector overlay
                    if (isWindowSelectorMode) {
                        WindowSelectorOverlay(
                            baseUrl = viewModel.backendUrl,
                            onExit = { viewModel.toggleWindowSelectorMode() },
                            onWindowSelected = { windowId ->
                                // Window was selected and focused
                            }
                        )
                    }

                    // Display switching overlay
                    if (isDisplaySwitching) {
                        Box(
                            modifier = Modifier
                                .fillMaxSize()
                                .background(Color.Black.copy(alpha = 0.6f)),
                            contentAlignment = Alignment.Center
                        ) {
                            Column(horizontalAlignment = Alignment.CenterHorizontally) {
                                CircularProgressIndicator(
                                    color = NeuroColors.Primary,
                                    strokeWidth = 2.dp,
                                    modifier = Modifier.size(32.dp)
                                )
                                Spacer(Modifier.height(8.dp))
                                Text("Switching display...", color = NeuroColors.TextMuted, fontSize = 12.sp)
                            }
                        }
                    }
                }
            }
        }

        Column(modifier = Modifier.fillMaxSize()) {
            if (!isFullscreen) {
                // Header
                ConversationHeader(
                    healthState = healthState,
                    selectedAgent = selectedAgent,
                    isSpeakEnabled = isSpeakEnabled,
                    onMenuClick = { viewModel.toggleSideDrawer() },
                    onAgentClick = { viewModel.toggleAgentDropdown() },
                    onHistoryClick = { viewModel.toggleChatHistoryDrawer() },
                    onNewTab = { viewModel.createNewTab() },
                    onSpeakToggle = { viewModel.toggleSpeak() }
                )

                // Tab bar
                TabBar(
                    tabs = openTabs[selectedAgent.type] ?: emptyList(),
                    onTabSelect = { cid -> viewModel.openConversation(cid) },
                    onTabClose = { cid -> viewModel.closeTab(cid) },
                    onTabRename = { cid, title -> viewModel.renameConversation(cid, title) },
                    onNewTab = { viewModel.createNewTab() },
                    onHistoryClick = { viewModel.toggleChatHistoryDrawer() }
                )
            }

            // Remote PC video container - shown when screen mode is active but not fullscreen
            if (isScreenMode && !isFullscreen) {
                Box(
                    modifier = Modifier
                        .fillMaxWidth()
                        .aspectRatio(16f / 9f)
                        .background(Color.Black)
                        .padding(horizontal = 16.dp, vertical = 8.dp)
                ) {
                    // Actual remote video track
                    videoTrack?.let { track ->
                        room?.let { r ->
                            CompositionLocalProvider(RoomLocal provides r) {
                                VideoTrackView(
                                    videoTrack = track,
                                    modifier = Modifier.fillMaxSize(),
                                    scaleType = ScaleType.FitInside
                                )
                            }
                        }
                    } ?: run {
                        // Placeholder if no track yet
                        Column(
                            modifier = Modifier.fillMaxSize(),
                            horizontalAlignment = Alignment.CenterHorizontally,
                            verticalArrangement = Arrangement.Center
                        ) {
                            Text(
                                text = "Waiting for stream...",
                                color = NeuroColors.TextPrimary,
                                fontSize = 14.sp
                            )
                        }
                    }

                    // Display switching overlay (non-fullscreen)
                    if (isDisplaySwitching) {
                        Box(
                            modifier = Modifier.fillMaxSize().background(Color.Black.copy(alpha = 0.6f)),
                            contentAlignment = Alignment.Center
                        ) {
                            CircularProgressIndicator(color = NeuroColors.Primary, strokeWidth = 2.dp, modifier = Modifier.size(24.dp))
                        }
                    }

                    // Enter fullscreen button
                    IconButton(
                        onClick = { viewModel.toggleFullscreen() },
                        modifier = Modifier
                            .align(Alignment.TopEnd)
                            .padding(4.dp)
                    ) {
                        Icon(
                            Icons.Default.Fullscreen,
                            contentDescription = "Enter Fullscreen",
                            tint = NeuroColors.TextPrimary
                        )
                    }
                }
            }

            if (!isFullscreen) {
                // Messages area - either chat list or active conversation
                if (activeTabCid != null) {
                    // Show active conversation messages
                    Box(modifier = Modifier.weight(1f).fillMaxWidth()) {
                        LazyColumn(
                            state = listState,
                            modifier = Modifier
                                .fillMaxSize()
                                .padding(horizontal = 12.dp)
                                .then(if (isTabLoading) Modifier.blur(3.dp) else Modifier),
                            verticalArrangement = Arrangement.spacedBy(6.dp),
                            contentPadding = PaddingValues(vertical = 8.dp)
                        ) {
                            items(tabMessages, key = { it.id }) { message ->
                                AnimatedMessageBubble(
                                    message = message,
                                    backendUrl = viewModel.backendUrl,
                                    isAutoPlaying = viewModel.playingMessageId.collectAsState().value == message.id
                                )
                            }

                            if (isLoading) {
                                item {
                                    ThinkingIndicator(agentName = selectedAgent.name)
                                }
                            }
                        }

                        if (isTabLoading) {
                            Box(
                                modifier = Modifier
                                    .fillMaxSize()
                                    .background(NeuroColors.BackgroundDark.copy(alpha = 0.4f)),
                                contentAlignment = Alignment.Center
                            ) {
                                CircularProgressIndicator(
                                    color = NeuroColors.Primary,
                                    strokeWidth = 2.dp,
                                    modifier = Modifier.size(32.dp)
                                )
                            }
                        }
                    }
                } else {
                    // Show recent conversations (first 5)
                    val allConversations = conversationsByAgent[selectedAgent.type] ?: emptyList()
                    val recentConversations = allConversations.take(5)
                    
                    Column(
                        modifier = Modifier
                            .weight(1f)
                            .fillMaxWidth()
                            .background(NeuroColors.BackgroundLight)
                            .padding(16.dp)
                    ) {
                        if (recentConversations.isEmpty()) {
                            Box(
                                modifier = Modifier
                                    .weight(1f)
                                    .fillMaxWidth(),
                                contentAlignment = Alignment.Center
                            ) {
                                Text(
                                    text = "No recent chats",
                                    color = NeuroColors.TextMuted,
                                    fontSize = 16.sp
                                )
                            }
                        } else {
                            Text(
                                text = "Recent",
                                color = NeuroColors.TextMuted,
                                fontSize = 14.sp,
                                modifier = Modifier.padding(bottom = 12.dp)
                            )
                            
                            recentConversations.forEach { conv ->
                                ChatListItem(
                                    conversation = conv,
                                    onClick = { viewModel.openConversation(conv.id) }
                                )
                                Spacer(modifier = Modifier.height(8.dp))
                            }
                            
                            // Show "View All" button if there are more than 5 conversations
                            if (allConversations.size > 5) {
                                Spacer(modifier = Modifier.height(8.dp))
                                TextButton(
                                    onClick = { viewModel.toggleChatHistoryDrawer() },
                                    modifier = Modifier.fillMaxWidth()
                                ) {
                                    Icon(
                                        imageVector = Icons.Default.History,
                                        contentDescription = null,
                                        tint = NeuroColors.Primary,
                                        modifier = Modifier.size(18.dp)
                                    )
                                    Spacer(modifier = Modifier.width(8.dp))
                                    Text(
                                        text = "View All (${allConversations.size})",
                                        color = NeuroColors.Primary
                                    )
                                }
                            }
                        }
                    }
                }
            }

            // Input bar area
            if (!isFullscreen) {
                // Attachment strip — sits directly above input bar
                if (isAttachmentMenuOpen && !showVoiceRecording) {
                    Row(
                        modifier = Modifier
                            .fillMaxWidth()
                            .background(Color(0xFF1C1C1E))
                            .padding(horizontal = 16.dp, vertical = 10.dp),
                        horizontalArrangement = Arrangement.SpaceEvenly
                    ) {
                        // Camera
                        Column(
                            horizontalAlignment = Alignment.CenterHorizontally,
                            modifier = Modifier.clickable { /* TODO */ viewModel.toggleAttachmentMenu() }
                                .padding(horizontal = 16.dp, vertical = 4.dp)
                        ) {
                            Box(
                                contentAlignment = Alignment.Center,
                                modifier = Modifier.size(44.dp).background(NeuroColors.Primary.copy(alpha = 0.12f), CircleShape)
                            ) {
                                Icon(Icons.Default.CameraAlt, null, tint = NeuroColors.Primary, modifier = Modifier.size(20.dp))
                            }
                            Spacer(Modifier.height(4.dp))
                            Text("Camera", color = NeuroColors.TextMuted, fontSize = 11.sp)
                        }
                        // Gallery
                        Column(
                            horizontalAlignment = Alignment.CenterHorizontally,
                            modifier = Modifier.clickable { /* TODO */ viewModel.toggleAttachmentMenu() }
                                .padding(horizontal = 16.dp, vertical = 4.dp)
                        ) {
                            Box(
                                contentAlignment = Alignment.Center,
                                modifier = Modifier.size(44.dp).background(Color(0xFF4CAF50).copy(alpha = 0.12f), CircleShape)
                            ) {
                                Icon(Icons.Default.Image, null, tint = Color(0xFF4CAF50), modifier = Modifier.size(20.dp))
                            }
                            Spacer(Modifier.height(4.dp))
                            Text("Gallery", color = NeuroColors.TextMuted, fontSize = 11.sp)
                        }
                        // File
                        Column(
                            horizontalAlignment = Alignment.CenterHorizontally,
                            modifier = Modifier.clickable { /* TODO */ viewModel.toggleAttachmentMenu() }
                                .padding(horizontal = 16.dp, vertical = 4.dp)
                        ) {
                            Box(
                                contentAlignment = Alignment.Center,
                                modifier = Modifier.size(44.dp).background(Color(0xFFFF9800).copy(alpha = 0.12f), CircleShape)
                            ) {
                                Icon(Icons.Default.AttachFile, null, tint = Color(0xFFFF9800), modifier = Modifier.size(20.dp))
                            }
                            Spacer(Modifier.height(4.dp))
                            Text("File", color = NeuroColors.TextMuted, fontSize = 11.sp)
                        }
                    }
                }

                if (showVoiceRecording) {
                    VoiceRecordingBar(
                        onCancel = { viewModel.toggleVoiceRecording() },
                        onSend = { viewModel.submitVoiceMessage(); viewModel.toggleVoiceRecording() },
                        onPause = { /* pause recording */ },
                        onResume = { /* resume recording */ }
                    )
                } else {
                    MessageInputBar(
                        text = inputText,
                        onTextChange = { viewModel.updateInputText(it) },
                        onSend = { viewModel.sendMessage() },
                        onVoiceClick = { viewModel.toggleVoiceRecording() },
                        isVoiceTyping = isVoiceTyping,
                        onVoiceTypeToggle = { viewModel.toggleVoiceTyping() },
                        isAttachmentMenuOpen = isAttachmentMenuOpen,
                        onAttachmentMenuToggle = { viewModel.toggleAttachmentMenu() }
                    )
                }
            }
        }

        // Attachment menu — horizontal strip directly above input bar
        if (isAttachmentMenuOpen) {
            // Dismiss scrim
            Box(
                modifier = Modifier
                    .fillMaxSize()
                    .clickable { viewModel.toggleAttachmentMenu() }
            )
        }

        // Side Drawer
        AnimatedVisibility(
            visible = showSideDrawer,
            enter = slideInHorizontally(initialOffsetX = { -it }) + fadeIn(),
            exit = slideOutHorizontally(targetOffsetX = { -it }) + fadeOut()
        ) {
            SideDrawerPanel(
                onClose = { viewModel.toggleSideDrawer() },
                onSettingsClick = { viewModel.toggleSettings() },
                onScreenShareClick = { viewModel.toggleScreenShare() },
                onVoiceSettingsClick = { /* TODO */ },
                onOcrClick = { /* TODO */ },
                onShortcutsClick = { /* TODO */ },
                onAboutClick = { /* TODO */ },
                onOverlayToggle = { viewModel.toggleOverlay() },
                remotePcConnected = isScreenMode,
                isOverlayEnabled = viewModel.isOverlayEnabled.collectAsState().value
            )
        }

        // Chat History Drawer
        if (showChatHistoryDrawer) {
            ChatHistoryDrawer(
                onClose = { viewModel.toggleChatHistoryDrawer() },
                onChatSelect = { cid -> viewModel.openConversation(cid) },
                onChatRename = { cid, title -> viewModel.renameConversation(cid, title) },
                onChatDelete = { cid -> viewModel.deleteConversation(cid) },
                conversations = conversationsByAgent[selectedAgent.type] ?: emptyList()
            )
        }

        // Settings Modal
        if (showSettings) {
            SettingsModal(
                onDismiss = { viewModel.toggleSettings() }
            )
        }

        // Agent Dropdown — suppressed in fullscreen/screen-sharing mode
        if (showAgentDropdown && !isFullscreen) {
            AgentDropdown(
                agents = AgentInfo.AGENTS,
                selectedAgent = selectedAgent,
                onSelect = { agent ->
                    viewModel.selectAgent(agent)
                },
                onDismiss = { viewModel.toggleAgentDropdown() },
                menuAlignment = if (isFullscreen) Alignment.TopEnd else Alignment.TopStart,
                menuOffset = if (isFullscreen) DpOffset((-16).dp, 60.dp) else DpOffset(60.dp, 110.dp)
            )
        }

        // Right-side static controls for fullscreen
        if (isFullscreen) {
            Column(
                modifier = Modifier
                    .align(Alignment.CenterEnd)
                    .padding(end = 8.dp)
                    .clip(RoundedCornerShape(32.dp))
                    .background(NeuroColors.BackgroundMid.copy(alpha = 0.45f))
                    .border(1.dp, NeuroColors.BorderSubtle.copy(alpha = 0.3f), RoundedCornerShape(32.dp))
                    .padding(vertical = 12.dp, horizontal = 4.dp),
                horizontalAlignment = Alignment.CenterHorizontally,
                verticalArrangement = Arrangement.spacedBy(12.dp)
            ) {
                // Mic (Voice Recording)
                IconButton(onClick = { viewModel.toggleVoiceRecording() }) {
                    Icon(Icons.Default.Mic, contentDescription = "Mic", tint = Color.White)
                }
                
                // Touch-mode cycle: NONE → TOUCHPAD → TABLET → NONE
                val touchMode by viewModel.touchMode.collectAsState()
                val touchIcon = when (touchMode) {
                    TouchMode.TOUCHPAD -> Icons.Default.Mouse
                    TouchMode.TABLET -> Icons.Default.TouchApp
                    TouchMode.NONE -> Icons.Default.DoNotTouch
                }
                val touchTint = when (touchMode) {
                    TouchMode.TOUCHPAD -> Color(0xFF8BE9FD.toInt())
                    TouchMode.TABLET -> Color(0xFFFFB86C.toInt())
                    TouchMode.NONE -> Color.White.copy(alpha = 0.6f)
                }
                val touchBg = when (touchMode) {
                    TouchMode.TOUCHPAD -> Color(0xFF8BE9FD.toInt()).copy(alpha = 0.2f)
                    TouchMode.TABLET -> Color(0xFFFFB86C.toInt()).copy(alpha = 0.2f)
                    TouchMode.NONE -> Color.Transparent
                }
                val touchDesc = when (touchMode) {
                    TouchMode.TOUCHPAD -> "Touchpad mode"
                    TouchMode.TABLET -> "Tablet mode"
                    TouchMode.NONE -> "Touch disabled"
                }
                IconButton(
                    onClick = { viewModel.cycleTouchMode() },
                    modifier = Modifier.background(touchBg, shape = CircleShape)
                ) {
                    Icon(touchIcon, contentDescription = touchDesc, tint = touchTint)
                }

                // Window Selector Toggle
                IconButton(
                    onClick = { viewModel.toggleWindowSelectorMode() },
                    modifier = Modifier.background(
                        if (isWindowSelectorMode) Color(0xFF50FA7B.toInt()).copy(alpha = 0.2f) else Color.Transparent,
                        shape = CircleShape
                    )
                ) {
                    Icon(Icons.Default.Window, contentDescription = "Window Selector", tint = if (isWindowSelectorMode) Color(0xFF50FA7B.toInt()) else Color.White)
                }

                // Switch Display
                IconButton(
                    onClick = { if (!isDisplaySwitching) viewModel.switchDisplay() },
                    enabled = !isDisplaySwitching
                ) {
                    if (isDisplaySwitching) {
                        CircularProgressIndicator(
                            modifier = Modifier.size(20.dp),
                            color = NeuroColors.Primary,
                            strokeWidth = 2.dp
                        )
                    } else {
                        Icon(Icons.Default.Monitor, contentDescription = "Switch Display", tint = Color.White)
                    }
                }

                // Stop Screen Share — fullscreen-exit is redundant now that
                // screen mode is always fullscreen; this button disconnects
                // the stream and returns to the normal chat view. Visible in
                // both portrait and landscape (parent column is anchored to
                // Alignment.CenterEnd regardless of orientation).
                IconButton(onClick = { viewModel.toggleScreenShare() }) {
                    Icon(
                        Icons.Default.StopScreenShare,
                        contentDescription = "Stop Screen Share",
                        tint = Color(0xFFFF6B6B.toInt()),
                    )
                }
            }
        }

        // Agent Selector at Top End — hidden in screen sharing / fullscreen mode

        // Left-side fixed Toolbar - only shown during fullscreen mode
        if (isFullscreen) {
            Box(
                modifier = Modifier
                    .align(Alignment.CenterStart)
                    .padding(start = 32.dp)
            ) {
                DraggableToolbarOverlay(
                    offset = Offset.Zero,
                    onOffsetChange = { /* fixed position */ },
                    isVoiceTyping = isVoiceTyping,
                    isKeyboardOpen = isKeyboardOpen,
                    isScrollMode = isScrollMode,
                    isClickMode = isClickMode,
                    isFocusMode = isFocusMode,
                    selectedAgentName = selectedAgent.name,
                    selectedAgentType = selectedAgent.type,
                    onVoiceTypeToggle = { viewModel.toggleVoiceTyping() },
                    onSubmitVoice = { viewModel.submitVoiceType(true) },
                    onCancelVoice = { viewModel.cancelVoiceRecording() },
                    onSendKey = { viewModel.sendKey(it) },
                    onToggleKeyboard = { viewModel.toggleKeyboard() },
                    onToggleScrollMode = { viewModel.toggleScrollMode() },
                    onToggleClickMode = { viewModel.toggleClickMode() },
                    onToggleFocusMode = { viewModel.toggleFocusMode() },
                    onAgentClick = { viewModel.toggleAgentDropdown() },
                    showAgentButton = false,
                    isRotationLocked = viewModel.rotationLockState.locked.collectAsState().value,
                    onRotationLockToggle = { viewModel.toggleRotationLock() },
                )
            }
        }

        // Full Keyboard Overlay - only shown during fullscreen mode
        // startPadding clears the left toolbar (32dp offset + ~48dp pill + 8dp gap)
        if (isFullscreen && isKeyboardOpen) {
            FullKeyboardOverlay(
                onKeyPress = { viewModel.sendKey(it) },
                onComboPress = { viewModel.sendKey(it) },
                onClose = { viewModel.toggleKeyboard() },
                startPadding = 88.dp,
            )
        }

        // Remote PC Connecting overlay
        if (isScreenConnecting) {
            Box(
                modifier = Modifier
                    .fillMaxSize()
                    .background(Color.Black.copy(alpha = 0.7f)),
                contentAlignment = Alignment.Center
            ) {
                Column(horizontalAlignment = Alignment.CenterHorizontally) {
                    CircularProgressIndicator(color = NeuroColors.Primary)
                    Spacer(modifier = Modifier.height(16.dp))
                    Text(
                        text = "Opening Remote Desktop...",
                        color = NeuroColors.TextPrimary,
                        fontSize = 16.sp
                    )
                }
            }
        }

        // Voice Connection Status
        when (val state = voiceConnectionState) {
            is VoiceConnectionState.Connected -> {
                VoiceConnectedOverlay(
                    roomName = state.roomName,
                    onDisconnect = { /* disconnect */ }
                )
            }
            is VoiceConnectionState.Connecting -> {
                VoiceConnectingOverlay()
            }
            is VoiceConnectionState.Error -> {
                VoiceErrorOverlay(
                    message = state.message,
                    onRetry = { /* retry */ }
                )
            }
            else -> {}
        }
    }
}

@Composable
fun ConversationHeader(
    healthState: BackendHealthState,
    selectedAgent: AgentInfo,
    isSpeakEnabled: Boolean,
    onMenuClick: () -> Unit,
    onAgentClick: () -> Unit,
    onHistoryClick: () -> Unit,
    onNewTab: () -> Unit,
    onSpeakToggle: () -> Unit
) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .background(NeuroColors.BackgroundMid)
            .padding(horizontal = 8.dp, vertical = 4.dp)
            .padding(top = 24.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        IconButton(onClick = onMenuClick) {
            Icon(
                Icons.Default.Menu,
                contentDescription = "Menu",
                tint = NeuroColors.TextPrimary
            )
        }

        Spacer(modifier = Modifier.width(8.dp))

        // Agent selector button
        Surface(
            color = NeuroColors.GlassPrimary,
            shape = RoundedCornerShape(8.dp),
            modifier = Modifier.clickable { onAgentClick() }
        ) {
            Row(
                modifier = Modifier.padding(horizontal = 10.dp, vertical = 6.dp),
                verticalAlignment = Alignment.CenterVertically
            ) {
                // Agent logo
                Box(
                    modifier = Modifier.size(20.dp),
                    contentAlignment = Alignment.Center
                ) {
                    when (selectedAgent.type) {
                        AgentType.NEURO -> androidx.compose.foundation.Image(
                            painter = painterResource(id = R.drawable.logo),
                            contentDescription = selectedAgent.name,
                            modifier = Modifier.fillMaxSize(),
                            contentScale = ContentScale.Fit
                        )
                        AgentType.OPENCLAW -> androidx.compose.foundation.Image(
                            painter = painterResource(id = R.drawable.openclaw_logo),
                            contentDescription = selectedAgent.name,
                            modifier = Modifier.fillMaxSize(),
                            contentScale = ContentScale.Fit
                        )
                        AgentType.OPENCODE -> androidx.compose.foundation.Image(
                            painter = painterResource(id = R.drawable.opencode_logo),
                            contentDescription = selectedAgent.name,
                            modifier = Modifier.fillMaxSize(),
                            contentScale = ContentScale.Fit
                        )
                        AgentType.NEUROUPWORK -> Image(
                            painter = painterResource(id = R.drawable.upwork_logo),
                            contentDescription = selectedAgent.name,
                            modifier = Modifier.fillMaxSize(),
                            contentScale = ContentScale.Fit
                        )
                    }
                }
                Spacer(modifier = Modifier.width(8.dp))
                Text(
                    text = selectedAgent.name,
                    color = NeuroColors.TextPrimary,
                    fontSize = 14.sp
                )
                Spacer(modifier = Modifier.width(4.dp))
                Icon(
                    Icons.Default.ArrowDropDown,
                    contentDescription = null,
                    tint = NeuroColors.TextMuted,
                    modifier = Modifier.size(20.dp)
                )
            }
        }

        Spacer(modifier = Modifier.width(8.dp))

        // History button
        IconButton(onClick = onHistoryClick) {
            Icon(
                imageVector = Icons.Default.History,
                contentDescription = "Chat History",
                tint = NeuroColors.TextPrimary,
                modifier = Modifier.size(20.dp)
            )
        }

        // New conversation button
        IconButton(onClick = onNewTab) {
            Icon(
                imageVector = Icons.Default.Add,
                contentDescription = "New Chat",
                tint = NeuroColors.Primary,
                modifier = Modifier.size(22.dp)
            )
        }

        // Speak toggle button
        IconButton(onClick = onSpeakToggle) {
            Icon(
                imageVector = if (isSpeakEnabled) Icons.Default.VolumeUp else Icons.Default.VolumeOff,
                contentDescription = if (isSpeakEnabled) "Disable TTS" else "Enable TTS",
                tint = if (isSpeakEnabled) NeuroColors.Primary else NeuroColors.TextMuted,
                modifier = Modifier.size(20.dp)
            )
        }

        Spacer(modifier = Modifier.weight(1f))

        // Connection status dot
        val dotColor = when (healthState) {
            is BackendHealthState.Healthy -> NeuroColors.Success
            is BackendHealthState.Unhealthy -> NeuroColors.Error
            is BackendHealthState.Checking -> NeuroColors.Primary
            else -> NeuroColors.TextDim
        }
        Box(
            modifier = Modifier
                .size(8.dp)
                .background(dotColor, CircleShape)
        )
    }
}

@Composable
fun AudioPlayer(
    autoPlayTrigger: kotlinx.coroutines.flow.StateFlow<Pair<String, String>?>,
    backendUrl: String,
    onPlayingChanged: (String?) -> Unit = {}
) {
    val trigger by autoPlayTrigger.collectAsState()
    val context = LocalContext.current
    var currentMediaPlayer by remember { mutableStateOf<android.media.MediaPlayer?>(null) }

    DisposableEffect(Unit) {
        onDispose {
            currentMediaPlayer?.release()
        }
    }

    LaunchedEffect(trigger) {
        val t = trigger ?: run {
            android.util.Log.d("AudioPlayer", "Trigger is null, skipping")
            return@LaunchedEffect
        }
        val (msgId, audioUrl) = t
        android.util.Log.d("AudioPlayer", "Auto-playing $msgId: $audioUrl")
        val fullUrl = if (audioUrl.startsWith("http")) audioUrl else "$backendUrl$audioUrl"
        android.util.Log.d("AudioPlayer", "Downloading from $fullUrl")
        withContext(Dispatchers.IO) {
            try {
                currentMediaPlayer?.release()
                val client = okhttp3.OkHttpClient.Builder()
                    .connectTimeout(10, java.util.concurrent.TimeUnit.SECONDS)
                    .readTimeout(15, java.util.concurrent.TimeUnit.SECONDS)
                    .build()
                val request = okhttp3.Request.Builder()
                    .url(fullUrl)
                    .header("ngrok-skip-browser-warning", "true")
                    .build()
                val response = client.newCall(request).execute()
                android.util.Log.d("AudioPlayer", "Response: ${response.code}")
                if (response.isSuccessful && response.body != null) {
                    val file = java.io.File(context.cacheDir, "voice_${System.currentTimeMillis()}.mp3")
                    file.writeBytes(response.body!!.bytes())
                    android.util.Log.d("AudioPlayer", "Downloaded ${file.length()} bytes to ${file.absolutePath}")
                    withContext(Dispatchers.Main) {
                        try {
                            currentMediaPlayer = android.media.MediaPlayer().apply {
                                setDataSource(file.absolutePath)
                                setOnPreparedListener {
                                    start()
                                    onPlayingChanged(msgId)
                                    android.util.Log.d("AudioPlayer", "Playing!")
                                }
                                setOnCompletionListener {
                                    release()
                                    currentMediaPlayer = null
                                    onPlayingChanged(null)
                                    file.delete()
                                }
                                setOnErrorListener { _, what, extra ->
                                    android.util.Log.e("AudioPlayer", "MediaPlayer error: what=$what extra=$extra")
                                    release()
                                    currentMediaPlayer = null
                                    file.delete()
                                    true
                                }
                                prepare()
                            }
                        } catch (e: Exception) {
                            android.util.Log.e("AudioPlayer", "MediaPlayer setup error: ${e.message}")
                        }
                    }
                } else {
                    android.util.Log.e("AudioPlayer", "Download failed: ${response.code}")
                }
            } catch (e: Exception) {
                android.util.Log.e("AudioPlayer", "Error: ${e.message}")
            }
        }
    }
}

@Composable
fun AnimatedMessageBubble(message: Message, backendUrl: String = "", isAutoPlaying: Boolean = false) {
    // Only animate messages less than 2 seconds old (freshly sent/received)
    val isNew = (System.currentTimeMillis() - message.timestamp) < 2000
    if (!isNew) {
        MessageBubble(message = message, backendUrl = backendUrl, isAutoPlaying = isAutoPlaying)
        return
    }

    var visible by remember { mutableStateOf(false) }
    LaunchedEffect(Unit) { visible = true }

    val offsetX = if (message.isUser) 24f else -24f
    val animatedOffset by animateFloatAsState(
        targetValue = if (visible) 0f else offsetX,
        animationSpec = spring(dampingRatio = 0.7f, stiffness = 400f),
        label = "slideX"
    )
    val animatedAlpha by animateFloatAsState(
        targetValue = if (visible) 1f else 0f,
        animationSpec = tween(200),
        label = "fadeIn"
    )

    Box(
        modifier = Modifier
            .offset { IntOffset(animatedOffset.roundToInt(), 0) }
            .alpha(animatedAlpha)
    ) {
        MessageBubble(message = message, backendUrl = backendUrl, isAutoPlaying = isAutoPlaying)
    }
}

@Composable
fun MessageBubble(message: Message, backendUrl: String = "", isAutoPlaying: Boolean = false) {
    val isUser = message.isUser
    var isPlaying by remember { mutableStateOf(false) }
    val effectivePlaying = isPlaying || isAutoPlaying
    var isLoading by remember { mutableStateOf(false) }
    var mediaPlayer by remember { mutableStateOf<android.media.MediaPlayer?>(null) }
    val scope = rememberCoroutineScope()
    val context = LocalContext.current

    DisposableEffect(Unit) { onDispose { mediaPlayer?.release() } }

    // WhatsApp-style asymmetric corners
    val bubbleShape = if (isUser)
        RoundedCornerShape(16.dp, 4.dp, 16.dp, 16.dp)
    else
        RoundedCornerShape(4.dp, 16.dp, 16.dp, 16.dp)

    val bgColor = if (isUser) Color(0xFF8B5CF6).copy(alpha = 0.18f) else Color(0xFF1C1C1E)

    Box(
        modifier = Modifier
            .fillMaxWidth()
            .padding(
                start = if (isUser) 48.dp else 0.dp,
                end = if (isUser) 0.dp else 48.dp
            ),
        contentAlignment = if (isUser) Alignment.CenterEnd else Alignment.CenterStart
    ) {
        Column(
            modifier = Modifier
                .clip(bubbleShape)
                .background(bgColor)
                .padding(horizontal = 10.dp, vertical = 7.dp)
        ) {
            if (message.isVoice) {
                // Single-row voice: play button + text + timestamp
                Row(verticalAlignment = Alignment.CenterVertically) {
                    // Play/stop button
                    Box(
                        contentAlignment = Alignment.Center,
                        modifier = Modifier
                            .size(30.dp)
                            .background(
                                if (effectivePlaying) NeuroColors.Error.copy(alpha = 0.15f)
                                else NeuroColors.Primary.copy(alpha = 0.12f),
                                CircleShape
                            )
                            .clickable {
                                if (effectivePlaying) {
                                    mediaPlayer?.stop(); mediaPlayer?.release(); mediaPlayer = null; isPlaying = false
                                } else if (message.audioUrl != null) {
                                    isLoading = true
                                    scope.launch(Dispatchers.IO) {
                                        try {
                                            val fullUrl = if (message.audioUrl!!.startsWith("http")) message.audioUrl!! else "$backendUrl${message.audioUrl}"
                                            val resp = okhttp3.OkHttpClient().newCall(okhttp3.Request.Builder().url(fullUrl).build()).execute()
                                            if (resp.isSuccessful && resp.body != null) {
                                                val f = java.io.File(context.cacheDir, "v_${System.currentTimeMillis()}.m4a")
                                                f.writeBytes(resp.body!!.bytes())
                                                withContext(Dispatchers.Main) {
                                                    mediaPlayer = android.media.MediaPlayer().apply {
                                                        setDataSource(f.absolutePath)
                                                        setOnPreparedListener { start(); isLoading = false; isPlaying = true }
                                                        setOnCompletionListener { isPlaying = false; release(); mediaPlayer = null; f.delete() }
                                                        setOnErrorListener { _, _, _ -> isPlaying = false; isLoading = false; release(); mediaPlayer = null; f.delete(); true }
                                                        prepare()
                                                    }
                                                }
                                            } else withContext(Dispatchers.Main) { isLoading = false }
                                        } catch (e: Exception) { withContext(Dispatchers.Main) { isLoading = false } }
                                    }
                                }
                            }
                    ) {
                        when {
                            isLoading -> CircularProgressIndicator(Modifier.size(12.dp), color = NeuroColors.TextMuted, strokeWidth = 1.5.dp)
                            effectivePlaying -> Icon(Icons.Default.Stop, null, tint = NeuroColors.Error, modifier = Modifier.size(14.dp))
                            message.audioUrl != null -> Icon(Icons.Default.PlayArrow, null, tint = NeuroColors.Primary, modifier = Modifier.size(14.dp))
                            !isUser -> CircularProgressIndicator(Modifier.size(10.dp), color = NeuroColors.Primary, strokeWidth = 1.5.dp)
                            else -> Icon(Icons.Default.Mic, null, tint = NeuroColors.TextMuted, modifier = Modifier.size(12.dp))
                        }
                    }

                    Spacer(Modifier.width(8.dp))

                    // Transcription text inline (or placeholder)
                    val displayText = if (message.text.isEmpty() || message.text == "(Transcribing...)") "Voice message" else message.text
                    Text(
                        text = displayText,
                        color = if (message.text.isEmpty() || message.text == "(Transcribing...)") NeuroColors.TextMuted else Color.White,
                        fontSize = 14.sp,
                        lineHeight = 18.sp,
                        modifier = Modifier.weight(1f)
                    )

                    Spacer(Modifier.width(6.dp))

                    Text(
                        SimpleDateFormat("HH:mm", Locale.getDefault()).format(Date(message.timestamp)),
                        color = NeuroColors.TextDim, fontSize = 10.sp
                    )
                }
            } else {
                // Plain text with inline timestamp (WhatsApp-style)
                val timeStr = SimpleDateFormat("HH:mm", Locale.getDefault()).format(Date(message.timestamp))
                // Append invisible timestamp-width spacer so real timestamp can overlay without clipping text
                val spacer = "  $timeStr"
                Box {
                    Text(
                        text = message.text + spacer,
                        color = Color.White,
                        fontSize = 14.sp,
                        lineHeight = 20.sp,
                        modifier = Modifier.alpha(0f) // invisible layout-only copy to reserve space
                    )
                    Text(
                        text = message.text,
                        color = Color.White,
                        fontSize = 14.sp,
                        lineHeight = 20.sp
                    )
                    Text(
                        text = timeStr,
                        color = NeuroColors.TextDim,
                        fontSize = 10.sp,
                        modifier = Modifier.align(Alignment.BottomEnd)
                    )
                }
            }
        }
    }
}

@Composable
fun MessageInputBar(
    text: String,
    onTextChange: (String) -> Unit,
    onSend: () -> Unit,
    onVoiceClick: () -> Unit,
    isVoiceTyping: Boolean,
    onVoiceTypeToggle: () -> Unit,
    isAttachmentMenuOpen: Boolean,
    onAttachmentMenuToggle: () -> Unit
) {
    Row(
        verticalAlignment = Alignment.Bottom,
        modifier = Modifier
            .fillMaxWidth()
            .background(Color(0xFF0A0A0A))
            .padding(horizontal = 8.dp, vertical = 6.dp)
            .padding(bottom = 20.dp)
            .imePadding()
    ) {
        // Attachment
        IconButton(
            onClick = onAttachmentMenuToggle,
            modifier = Modifier.size(36.dp)
        ) {
            Icon(Icons.Default.AttachFile, null, tint = NeuroColors.TextMuted, modifier = Modifier.size(20.dp))
        }

        // Input field — grows with content, max 4 lines
        BasicTextField(
            value = text,
            onValueChange = onTextChange,
            modifier = Modifier
                .weight(1f)
                .heightIn(min = 40.dp, max = 120.dp)
                .clip(RoundedCornerShape(20.dp))
                .background(Color(0xFF1C1C1E))
                .padding(horizontal = 14.dp, vertical = 10.dp),
            textStyle = LocalTextStyle.current.copy(color = Color.White, fontSize = 15.sp, lineHeight = 20.sp),
            cursorBrush = SolidColor(NeuroColors.Primary),
            keyboardOptions = KeyboardOptions(imeAction = ImeAction.Send),
            keyboardActions = KeyboardActions(onSend = { onSend() }),
            maxLines = 4,
            decorationBox = { innerTextField ->
                Box(contentAlignment = Alignment.CenterStart) {
                    if (text.isEmpty()) {
                        Text("Message", color = NeuroColors.TextDim, fontSize = 15.sp)
                    }
                    innerTextField()
                }
            }
        )

        Spacer(Modifier.width(6.dp))

        // Send / Mic button
        if (text.isNotBlank()) {
            IconButton(
                onClick = onSend,
                modifier = Modifier
                    .size(36.dp)
                    .background(NeuroColors.Primary, CircleShape)
            ) {
                Icon(Icons.AutoMirrored.Filled.Send, null, tint = Color.White, modifier = Modifier.size(18.dp))
            }
        } else {
            IconButton(
                onClick = onVoiceClick,
                modifier = Modifier.size(36.dp)
            ) {
                Icon(Icons.Default.Mic, null, tint = NeuroColors.Primary, modifier = Modifier.size(22.dp))
            }
        }
    }
}

@Composable
fun ThinkingIndicator(agentName: String = "Neuro") {
    val infiniteTransition = rememberInfiniteTransition(label = "think")

    Row(
        modifier = Modifier.fillMaxWidth().padding(start = 0.dp, end = 48.dp, top = 2.dp, bottom = 2.dp),
        horizontalArrangement = Arrangement.Start
    ) {
        Row(
            modifier = Modifier
                .clip(RoundedCornerShape(4.dp, 16.dp, 16.dp, 16.dp))
                .background(Color(0xFF1C1C1E))
                .padding(horizontal = 12.dp, vertical = 8.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            // Animated dots with staggered purple pulse
            repeat(3) { i ->
                val delay = i * 200
                val alpha by infiniteTransition.animateFloat(
                    initialValue = 0.25f,
                    targetValue = 1f,
                    animationSpec = infiniteRepeatable(
                        animation = tween(600, delayMillis = delay, easing = LinearEasing),
                        repeatMode = RepeatMode.Reverse
                    ),
                    label = "dot$i"
                )
                val scale by infiniteTransition.animateFloat(
                    initialValue = 0.7f,
                    targetValue = 1.0f,
                    animationSpec = infiniteRepeatable(
                        animation = tween(600, delayMillis = delay, easing = LinearEasing),
                        repeatMode = RepeatMode.Reverse
                    ),
                    label = "scale$i"
                )
                Box(
                    modifier = Modifier
                        .size((6 * scale).dp)
                        .background(NeuroColors.Primary.copy(alpha = alpha), CircleShape)
                )
                if (i < 2) Spacer(Modifier.width(4.dp))
            }

            Spacer(Modifier.width(8.dp))

            Text(
                text = "$agentName is thinking",
                color = NeuroColors.TextMuted,
                fontSize = 12.sp
            )
        }
    }
}

@Composable
fun VoiceRecordingBar(
    onCancel: () -> Unit,
    onSend: () -> Unit,
    onPause: () -> Unit,
    onResume: () -> Unit
) {
    var showCancelDialog by remember { mutableStateOf(false) }
    var isPaused by remember { mutableStateOf(false) }
    val infiniteTransition = rememberInfiniteTransition(label = "rec")

    // Pulsing red dot
    val dotAlpha by infiniteTransition.animateFloat(
        initialValue = 0.4f, targetValue = 1f,
        animationSpec = infiniteRepeatable(tween(800, easing = LinearEasing), RepeatMode.Reverse),
        label = "dot"
    )

    if (showCancelDialog) {
        AlertDialog(
            onDismissRequest = { showCancelDialog = false },
            title = { Text("Discard?", color = Color.White, fontSize = 16.sp) },
            text = { Text("Voice message will be discarded.", color = NeuroColors.TextSecondary, fontSize = 14.sp) },
            confirmButton = {
                TextButton(onClick = { showCancelDialog = false; onCancel() }) {
                    Text("Discard", color = NeuroColors.Error)
                }
            },
            dismissButton = {
                TextButton(onClick = { showCancelDialog = false }) {
                    Text("Keep", color = Color.White)
                }
            },
            containerColor = Color(0xFF1C1C1E),
            shape = RoundedCornerShape(16.dp)
        )
    }

    Row(
        verticalAlignment = Alignment.CenterVertically,
        modifier = Modifier
            .fillMaxWidth()
            .background(Color(0xFF0A0A0A))
            .padding(horizontal = 8.dp, vertical = 8.dp)
            .padding(bottom = 20.dp)
    ) {
        // Cancel
        IconButton(onClick = { showCancelDialog = true }, modifier = Modifier.size(36.dp)) {
            Icon(Icons.Default.Close, null, tint = NeuroColors.TextMuted, modifier = Modifier.size(20.dp))
        }

        // Waveform + recording indicator
        Row(
            verticalAlignment = Alignment.CenterVertically,
            modifier = Modifier
                .weight(1f)
                .height(40.dp)
                .clip(RoundedCornerShape(20.dp))
                .background(Color(0xFF1C1C1E))
                .padding(horizontal = 12.dp)
        ) {
            // Red pulsing dot
            Box(
                Modifier
                    .size(8.dp)
                    .background(
                        if (isPaused) NeuroColors.TextMuted else NeuroColors.Error.copy(alpha = dotAlpha),
                        CircleShape
                    )
            )
            Spacer(Modifier.width(8.dp))

            // Animated waveform bars
            Row(
                verticalAlignment = Alignment.CenterVertically,
                modifier = Modifier.weight(1f).height(24.dp),
                horizontalArrangement = Arrangement.Center
            ) {
                repeat(24) { i ->
                    val h by infiniteTransition.animateFloat(
                        initialValue = 3f,
                        targetValue = if (isPaused) 3f else (6f + (i % 5) * 3f),
                        animationSpec = infiniteRepeatable(
                            tween(250 + (i * 20), easing = LinearEasing), RepeatMode.Reverse
                        ),
                        label = "b$i"
                    )
                    Box(
                        Modifier
                            .width(2.dp)
                            .height(h.dp)
                            .padding(horizontal = 0.5.dp)
                            .background(
                                if (isPaused) NeuroColors.TextDim else NeuroColors.Primary.copy(alpha = 0.8f),
                                RoundedCornerShape(1.dp)
                            )
                    )
                }
            }

            Spacer(Modifier.width(8.dp))

            // Pause/Resume
            Box(
                contentAlignment = Alignment.Center,
                modifier = Modifier
                    .size(28.dp)
                    .clickable { isPaused = !isPaused; if (isPaused) onPause() else onResume() }
            ) {
                Icon(
                    if (isPaused) Icons.Default.PlayArrow else Icons.Default.Pause,
                    null, tint = NeuroColors.Primary, modifier = Modifier.size(18.dp)
                )
            }
        }

        Spacer(Modifier.width(6.dp))

        // Send
        IconButton(
            onClick = onSend,
            modifier = Modifier.size(36.dp).background(NeuroColors.Primary, CircleShape)
        ) {
            Icon(Icons.AutoMirrored.Filled.Send, null, tint = Color.White, modifier = Modifier.size(18.dp))
        }
    }
}
