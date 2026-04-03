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

@HiltViewModel
class ConversationViewModel @Inject constructor(
    private val webSocketService: WebSocketService,
    private val chatDataChannelService: ChatDataChannelService,
    private val voiceService: VoiceService,
    private val backendUrlRepository: BackendUrlRepository,
    private val startupRepository: StartupRepository,
    private val openClawService: OpenClawService,
    private val liveKitService: LiveKitService,
    @dagger.hilt.android.qualifiers.ApplicationContext private val context: android.content.Context
) : ViewModel() {

    private val _messages = MutableStateFlow<List<Message>>(emptyList())
    val messages: StateFlow<List<Message>> = _messages.asStateFlow()

    private val _inputText = MutableStateFlow("")
    val inputText: StateFlow<String> = _inputText.asStateFlow()

    private val _isLoading = MutableStateFlow(false)
    val isLoading: StateFlow<Boolean> = _isLoading.asStateFlow()

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

    // Touchpad mode
    private val _isTouchpadMode = MutableStateFlow(false)
    val isTouchpadMode: StateFlow<Boolean> = _isTouchpadMode.asStateFlow()

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

    // Remote PC state
    private val _isScreenMode = MutableStateFlow(false)
    val isScreenMode: StateFlow<Boolean> = _isScreenMode.asStateFlow()

    private val _isFullscreen = MutableStateFlow(false)
    val isFullscreen: StateFlow<Boolean> = _isFullscreen.asStateFlow()

    private val _isScreenConnecting = MutableStateFlow(false)
    val isScreenConnecting: StateFlow<Boolean> = _isScreenConnecting.asStateFlow()

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
                        val speakOn = _isSpeakEnabled.value
                        val newMsg = Message(
                            id = msg.messageId,
                            text = msg.text,
                            isUser = false,  // Only agent messages come in here now
                            isVoice = speakOn
                        )
                        _tabMessages.value = _tabMessages.value + newMsg
                        _isLoading.value = false
                        android.util.Log.d("ChatDC", "Updated _tabMessages, count=${_tabMessages.value.size}")
                        
                        if (_isSpeakEnabled.value && msg.text.isNotEmpty()) {
                            if (msg.origin != "overlay") {
                                android.util.Log.d("ChatDC", "Calling generateTts for msg ${newMsg.id}")
                                generateTts(newMsg.id, msg.text)
                            } else {
                                android.util.Log.d("ChatDC", "Skipping TTS: msg.origin is overlay")
                            }
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

        // If no active tab, create a new conversation first
        if (_activeTabCid.value == null) {
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
                val reqBody = """{"text":"$text","cid":"$cid","voice":"alloy"}"""
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
                        msg.copy(audioUrl = audioUrl, isVoice = true)
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
                        // Open the new conversation
                        openConversation(cid)
                        // Now send the message
                        _tabMessages.value = _tabMessages.value + Message(
                            id = "user_${UUID.randomUUID()}",
                            text = text,
                            isUser = true
                        )
                        _isLoading.value = true
                        webSocketService.markMessageOrigin("app")
                        val result = webSocketService.sendMessage(text, cid = cid)
                        if (result.isFailure) {
                            _isLoading.value = false
                            _tabMessages.value = _tabMessages.value + Message(
                                id = "error_${UUID.randomUUID()}",
                                text = "Failed to send: ${result.exceptionOrNull()?.message}",
                                isUser = false
                            )
                        }
                    }
                }
            } catch (e: Exception) {
                android.util.Log.e("ConversationVM", "Failed to create conversation and send", e)
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
        val agent = selectedAgent.value.type
        // Add to open tabs if not already there
        val currentTabs = _openTabs.value.toMutableMap()
        val agentTabs = currentTabs[agent]?.toMutableList() ?: mutableListOf()

        if (agentTabs.none { it.cid == cid }) {
            // Get title from conversations list
            val convList = _conversationsByAgent.value[agent] ?: emptyList()
            val title = convList.find { it.id == cid }?.title ?: "New Chat"
            agentTabs.add(Tab(cid = cid, title = title, isActive = true))
        }

        // Mark selected tab as active
        val updatedTabs = agentTabs.map { it.copy(isActive = it.cid == cid) }
        currentTabs[agent] = updatedTabs
        _openTabs.value = currentTabs

        // Set active tab CID
        _activeTabCid.value = cid

        // Load messages for this conversation
        loadMessages(cid)
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
                        // Open the new conversation
                        openConversation(cid)
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
            }
        }
    }

    fun toggleTouchpadMode() {
        _isTouchpadMode.value = !_isTouchpadMode.value
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

    // MediaRecorder setup for voice typing
    private var mediaRecorder: android.media.MediaRecorder? = null
    private var voiceFile: java.io.File? = null

    fun toggleVoiceTyping() {
        if (_isVoiceTyping.value) {
            submitVoiceType(false)
        } else {
            startVoiceRecording()
        }
    }

    private fun startVoiceRecording() {
        try {
            // Check runtime permission
            val permCheck = android.content.pm.PackageManager.PERMISSION_GRANTED ==
                androidx.core.content.ContextCompat.checkSelfPermission(
                    context, android.Manifest.permission.RECORD_AUDIO
                )
            if (!permCheck) {
                android.util.Log.e("VoiceType", "RECORD_AUDIO permission not granted!")
                _isVoiceTyping.value = false
                return
            }

            voiceFile = java.io.File(context.cacheDir, "voice_type_${System.currentTimeMillis()}.m4a")
            android.util.Log.d("VoiceType", "Starting recording to: ${voiceFile?.absolutePath}")
            mediaRecorder = android.media.MediaRecorder().apply {
                setAudioSource(android.media.MediaRecorder.AudioSource.MIC)
                setOutputFormat(android.media.MediaRecorder.OutputFormat.MPEG_4)
                setAudioEncoder(android.media.MediaRecorder.AudioEncoder.AAC)
                setOutputFile(voiceFile?.absolutePath)
                prepare()
                start()
            }
            _isVoiceTyping.value = true
            android.util.Log.d("VoiceType", "Recording started")
        } catch (e: Exception) {
            android.util.Log.e("VoiceType", "Failed to start recording: ${e.message}", e)
            _isVoiceTyping.value = false
        }
    }

    fun submitVoiceType(pressEnter: Boolean = true) {
        if (!_isVoiceTyping.value) return
        android.util.Log.d("VoiceType", "Submitting voice type (pressEnter=$pressEnter)")
        try {
            mediaRecorder?.stop()
            mediaRecorder?.release()
            mediaRecorder = null
            _isVoiceTyping.value = false

            // Upload the file
            viewModelScope.launch(kotlinx.coroutines.Dispatchers.IO) {
                voiceFile?.let { file ->
                    val baseUrl = backendUrlRepository.currentUrl.value
                    val endpoint = if (pressEnter) "$baseUrl/voice-type?press_enter=true" else "$baseUrl/voice-type"
                    android.util.Log.d("VoiceType", "Uploading ${file.length()} bytes to $endpoint")
                    
                    val requestBody = okhttp3.MultipartBody.Builder()
                        .setType(okhttp3.MultipartBody.FORM)
                        .addFormDataPart("file", file.name, file.readBytes().toRequestBody("audio/m4a".toMediaType()))
                        .build()

                    val request = okhttp3.Request.Builder()
                        .url(endpoint)
                        .post(requestBody)
                        .header("ngrok-skip-browser-warning", "true")
                        .build()

                    try {
                        okhttp3.OkHttpClient().newCall(request).execute().use { response ->
                            val body = response.body?.string()
                            android.util.Log.d("VoiceType", "Response ${response.code}: $body")
                        }
                    } catch (e: Exception) {
                        android.util.Log.e("VoiceType", "Upload failed: ${e.message}", e)
                    }
                }
            }
        } catch (e: Exception) {
            android.util.Log.e("VoiceType", "Submit failed: ${e.message}", e)
            _isVoiceTyping.value = false
        }
    }

    fun cancelVoiceRecording() {
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
            webSocketService.markMessageOrigin("app")
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

                        // Replace placeholder in-place with transcription + audio URL
                        _tabMessages.value = _tabMessages.value.map { msg ->
                            if (msg.id == placeholderId) msg.copy(
                                text = transcription.ifEmpty { "(No transcription)" },
                                isVoice = true,
                                audioUrl = audioUrl
                            ) else msg
                        }
                        // WS will deliver the assistant reply — no polling needed
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
        viewModelScope.launch(kotlinx.coroutines.Dispatchers.IO) {
            val baseUrl = backendUrlRepository.currentUrl.value
            val request = okhttp3.Request.Builder()
                .url("$baseUrl/screen/switch-display")
                .post(ByteArray(0).toRequestBody(null))
                .header("ngrok-skip-browser-warning", "true")
                .build()

            try {
                okhttp3.OkHttpClient().newCall(request).execute().close()
            } catch (e: Exception) {
                e.printStackTrace()
            }
        }
    }

    fun toggleFullscreen() {
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

    fun sendMouseScroll(dx: Float, dy: Float) {
        liveKitService.sendMouseScroll(dx, dy)
    }

    override fun onCleared() {
        super.onCleared()
        webSocketService.disconnect()
        mediaRecorder?.release()
        mediaRecorder = null
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

    // Handle screen orientation and immersive mode for fullscreen
    DisposableEffect(isFullscreen) {
        val activity = context as? Activity
        val window = activity?.window
        if (window != null) {
            val controller = WindowCompat.getInsetsController(window, window.decorView)
            if (isFullscreen) {
                activity?.requestedOrientation = ActivityInfo.SCREEN_ORIENTATION_SENSOR_LANDSCAPE
                controller.hide(WindowInsetsCompat.Type.systemBars())
                controller.systemBarsBehavior = WindowInsetsControllerCompat.BEHAVIOR_SHOW_TRANSIENT_BARS_BY_SWIPE
            } else {
                activity?.requestedOrientation = ActivityInfo.SCREEN_ORIENTATION_UNSPECIFIED
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
        android.util.Log.d("ScrollDebug", "tabMessages.size=${tabMessages.size}")
        if (tabMessages.isNotEmpty()) {
            listState.animateScrollToItem(tabMessages.size - 1)
        }
    }

    // Audio player for auto-play (outside LazyColumn so not recycled)
    AudioPlayer(
        autoPlayTrigger = viewModel.autoPlayTrigger,
        backendUrl = viewModel.backendUrl
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
                // Inner container: height-constrained to fit the landscape screen.
                // In landscape, the phone is wider than 16:9, so we constrain by height
                // and let aspectRatio compute the width. This avoids vertical overflow/cropping.
                Box(
                    modifier = Modifier
                        .fillMaxHeight()
                        .aspectRatio(16f / 9f)
                        .border(1.dp, borderColor)
                ) {
                    videoTrack?.let { track ->
                        room?.let { r ->
                            CompositionLocalProvider(RoomLocal provides r) {
                                VideoTrackView(
                                    videoTrack = track,
                                    modifier = Modifier.fillMaxSize()
                                )
                            }
                        }
                    }
                    // Transparent gesture layer when touchpad mode is on
                    if (isTouchpadMode) {
                        TouchpadOverlay(
                            isScrollMode = isScrollMode,
                            isClickMode = isClickMode,
                            isFocusMode = isFocusMode,
                            onExit = { viewModel.toggleTouchpadMode() },
                            onMouseMove = { dx, dy -> viewModel.sendMouseMove(dx, dy) },
                            onMouseClick = { x, y, button -> viewModel.sendMouseClick(x, y, button) },
                            onMouseScroll = { dx, dy -> viewModel.sendMouseScroll(dx, dy) }
                        )
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
                                    modifier = Modifier.fillMaxSize()
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
                    LazyColumn(
                        state = listState,
                        modifier = Modifier
                            .weight(1f)
                            .fillMaxWidth()
                            .padding(horizontal = 16.dp),
                        verticalArrangement = Arrangement.spacedBy(8.dp),
                        contentPadding = PaddingValues(vertical = 16.dp)
                    ) {
                        items(tabMessages, key = { it.id }) { message ->
                            MessageBubble(message = message)
                        }

                        if (isLoading) {
                            item {
                                ThinkingIndicator(agentName = selectedAgent.name)
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

            // Voice Recording Modal
            if (showVoiceRecording) {
                VoiceRecordingPanel(
                    onDismiss = { viewModel.toggleVoiceRecording() },
                    onSend = { viewModel.sendMessage() }
                )
            }

            // Input bar
            if (!isFullscreen) {
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

        // Attachment Menu Popup
        if (isAttachmentMenuOpen) {
            Box(
                modifier = Modifier
                    .fillMaxSize()
                    .clickable(enabled = true) { viewModel.toggleAttachmentMenu() }
                    .background(Color.Black.copy(alpha = 0.3f)),
                contentAlignment = Alignment.BottomStart
            ) {
                Column(
                    modifier = Modifier
                        .align(Alignment.BottomStart)
                        .offset(y = (-80).dp)
                        .padding(start = 16.dp, bottom = 100.dp)
                        .clip(RoundedCornerShape(16.dp))
                        .background(NeuroColors.BackgroundMid)
                        .border(1.dp, NeuroColors.BorderSubtle, RoundedCornerShape(16.dp))
                        .padding(vertical = 8.dp)
                ) {
                    Row(
                        modifier = Modifier
                            .fillMaxWidth()
                            .clickable { /* TODO: Open camera */ viewModel.toggleAttachmentMenu() }
                            .padding(horizontal = 16.dp, vertical = 12.dp),
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Icon(Icons.Default.CameraAlt, contentDescription = null, tint = NeuroColors.Primary, modifier = Modifier.size(20.dp))
                        Spacer(modifier = Modifier.width(12.dp))
                        Text("Camera", color = NeuroColors.TextPrimary, fontSize = 14.sp)
                    }
                    Row(
                        modifier = Modifier
                            .fillMaxWidth()
                            .clickable { /* TODO: Open gallery */ viewModel.toggleAttachmentMenu() }
                            .padding(horizontal = 16.dp, vertical = 12.dp),
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Icon(Icons.Default.Image, contentDescription = null, tint = NeuroColors.Primary, modifier = Modifier.size(20.dp))
                        Spacer(modifier = Modifier.width(12.dp))
                        Text("Gallery", color = NeuroColors.TextPrimary, fontSize = 14.sp)
                    }
                    Row(
                        modifier = Modifier
                            .fillMaxWidth()
                            .clickable { /* TODO: Open file picker */ viewModel.toggleAttachmentMenu() }
                            .padding(horizontal = 16.dp, vertical = 12.dp),
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Icon(Icons.Default.AttachFile, contentDescription = null, tint = NeuroColors.Primary, modifier = Modifier.size(20.dp))
                        Spacer(modifier = Modifier.width(12.dp))
                        Text("File", color = NeuroColors.TextPrimary, fontSize = 14.sp)
                    }
                }
            }
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

        // Agent Dropdown
        if (showAgentDropdown) {
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
                
                // Mouse Control Toggle
                IconButton(
                    onClick = { viewModel.toggleTouchpadMode() },
                    modifier = Modifier.background(
                        if (isTouchpadMode) Color(0xFF8BE9FD.toInt()).copy(alpha = 0.2f) else Color.Transparent,
                        shape = CircleShape
                    )
                ) {
                    Icon(Icons.Default.Mouse, contentDescription = "Mouse Control", tint = if (isTouchpadMode) Color(0xFF8BE9FD.toInt()) else Color.White)
                }

                // Switch Display
                IconButton(onClick = { viewModel.switchDisplay() }) {
                    Icon(Icons.Default.Monitor, contentDescription = "Switch Display", tint = Color.White)
                }

                // Fullscreen Exit
                IconButton(onClick = { viewModel.toggleFullscreen() }) {
                    Icon(Icons.Default.FullscreenExit, contentDescription = "Exit Fullscreen", tint = Color.White)
                }
            }
        }

        // Agent Selector at Top End for Fullscreen
        if (isFullscreen) {
            Box(
                modifier = Modifier
                    .align(Alignment.TopEnd)
                    .padding(top = 0.dp, end = 16.dp)
            ) {
                AgentToolbarButton(
                    agentName = selectedAgent.name,
                    agentType = selectedAgent.type,
                    onClick = { viewModel.toggleAgentDropdown() }
                )
            }
        }

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
                    showAgentButton = false
                )
            }
        }

        // Full Keyboard Overlay - only shown during fullscreen mode
        if (isFullscreen && isKeyboardOpen) {
            FullKeyboardOverlay(
                onKeyPress = { viewModel.sendKey(it) },
                onComboPress = { viewModel.sendKey(it) },
                onClose = { viewModel.toggleKeyboard() }
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
    backendUrl: String
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
                                setOnPreparedListener { start(); android.util.Log.d("AudioPlayer", "Playing!") }
                                setOnCompletionListener {
                                    release()
                                    currentMediaPlayer = null
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
fun MessageBubble(message: Message) {
    val alignment = if (message.isUser) Alignment.CenterEnd else Alignment.CenterStart
    val backgroundColor = if (message.isUser) NeuroColors.GlassUserBubble else NeuroColors.GlassAssistantBubble
    val borderColor = if (message.isUser) NeuroColors.BorderAccent.copy(alpha = 0.35f) else NeuroColors.BorderSubtle
    var isPlaying by remember { mutableStateOf(false) }
    var isLoading by remember { mutableStateOf(false) }
    var mediaPlayer by remember { mutableStateOf<android.media.MediaPlayer?>(null) }
    val scope = rememberCoroutineScope()
    val context = LocalContext.current

    DisposableEffect(Unit) {
        onDispose {
            mediaPlayer?.release()
        }
    }

    Box(
        modifier = Modifier.fillMaxWidth(),
        contentAlignment = alignment
    ) {
        Column(
            modifier = Modifier
                .widthIn(max = 300.dp)
                .clip(RoundedCornerShape(16.dp))
                .background(backgroundColor)
                .border(1.dp, borderColor, RoundedCornerShape(16.dp))
                .padding(12.dp)
        ) {
            android.util.Log.d("MsgBubble", "id=${message.id} isVoice=${message.isVoice} audioUrl=${message.audioUrl} isUser=${message.isUser}")
            if (message.isVoice) {
                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    modifier = Modifier.fillMaxWidth()
                ) {
                    IconButton(
                        onClick = {
                            if (isPlaying) {
                                mediaPlayer?.stop()
                                mediaPlayer?.release()
                                mediaPlayer = null
                                isPlaying = false
                            } else if (message.audioUrl != null) {
                                isLoading = true
                                scope.launch(Dispatchers.IO) {
                                    try {
                                        val audioUrl = message.audioUrl!!
                                        val fullUrl = if (audioUrl.startsWith("http")) audioUrl else "https://5148-152-58-121-41.ngrok-free.app$audioUrl"
                                        val client = okhttp3.OkHttpClient()
                                        val request = okhttp3.Request.Builder().url(fullUrl).build()
                                        client.newCall(request).execute().use { response ->
                                            if (response.isSuccessful && response.body != null) {
                                                val file = java.io.File(context.cacheDir, "voice_${System.currentTimeMillis()}.m4a")
                                                file.parentFile?.mkdirs()
                                                file.writeBytes(response.body!!.bytes())
                                                android.util.Log.d("VoicePlay", "Downloaded to ${file.absolutePath}")
                                                withContext(Dispatchers.Main) {
                                                    try {
                                                        mediaPlayer = android.media.MediaPlayer().apply {
                                                            setDataSource(file.absolutePath)
                                                            setOnPreparedListener { start(); isLoading = false; isPlaying = true }
                                                            setOnCompletionListener {
                                                                isPlaying = false
                                                                release()
                                                                mediaPlayer = null
                                                                file.delete()
                                                            }
                                                            setOnErrorListener { _, _, _ ->
                                                                isPlaying = false
                                                                isLoading = false
                                                                release()
                                                                mediaPlayer = null
                                                                file.delete()
                                                                true
                                                            }
                                                            prepare()
                                                        }
                                                    } catch (e: Exception) {
                                                        android.util.Log.e("VoicePlay", "Play error: ${e.message}")
                                                        isLoading = false
                                                        file.delete()
                                                    }
                                                }
                                            } else {
                                                android.util.Log.e("VoicePlay", "Download failed: ${response.code}")
                                                withContext(Dispatchers.Main) {
                                                    isLoading = false
                                                }
                                            }
                                        }
                                    } catch (e: Exception) {
                                        android.util.Log.e("VoicePlay", "Error: ${e.message}")
                                        withContext(Dispatchers.Main) {
                                            isLoading = false
                                        }
                                    }
                                }
                            }
                        },
                        modifier = Modifier
                            .size(36.dp)
                            .background(
                                when {
                                    isLoading -> NeuroColors.TextMuted.copy(alpha = 0.2f)
                                    isPlaying -> NeuroColors.Error.copy(alpha = 0.2f)
                                    else -> NeuroColors.Primary.copy(alpha = 0.2f)
                                },
                                CircleShape
                            )
                    ) {
                        when {
                            isLoading || (message.isVoice && message.audioUrl == null) -> CircularProgressIndicator(
                                modifier = Modifier.size(16.dp),
                                color = NeuroColors.TextMuted,
                                strokeWidth = 2.dp
                            )
                            isPlaying -> Icon(
                                Icons.Default.Stop,
                                contentDescription = "Stop",
                                tint = NeuroColors.Error,
                                modifier = Modifier.size(20.dp)
                            )
                            else -> Icon(
                                Icons.Default.PlayArrow,
                                contentDescription = "Play voice",
                                tint = NeuroColors.Primary,
                                modifier = Modifier.size(20.dp)
                            )
                        }
                    }
                    Spacer(modifier = Modifier.width(8.dp))
                    Icon(
                        Icons.Default.Mic,
                        contentDescription = null,
                        tint = NeuroColors.TextMuted,
                        modifier = Modifier.size(14.dp)
                    )
                    Spacer(modifier = Modifier.width(6.dp))
                    Text(
                        text = message.text,
                        color = NeuroColors.TextPrimary,
                        fontSize = 14.sp,
                        modifier = Modifier.weight(1f)
                    )
                }
            } else {
                Text(
                    text = message.text,
                    color = NeuroColors.TextPrimary,
                    fontSize = 14.sp
                )
            }

            Spacer(modifier = Modifier.height(4.dp))

            Text(
                text = SimpleDateFormat("HH:mm", Locale.getDefault()).format(Date(message.timestamp)),
                color = NeuroColors.TextDim,
                fontSize = 10.sp,
                modifier = Modifier.align(Alignment.End)
            )
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
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .background(NeuroColors.BackgroundMid)
            .padding(horizontal = 16.dp, vertical = 4.dp)
            .padding(bottom = 24.dp)
            .imePadding()
    ) {
        // Typing Preview - floating pill above input
        if (text.isNotBlank()) {
            Box(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(bottom = 4.dp)
            ) {
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .clip(RoundedCornerShape(20.dp))
                        .background(
                            brush = androidx.compose.ui.graphics.Brush.horizontalGradient(
                                colors = listOf(
                                    NeuroColors.Primary.copy(alpha = 0.3f),
                                    NeuroColors.GlassAccent.copy(alpha = 0.4f)
                                )
                            )
                        )
                        .border(
                            width = 1.dp,
                            brush = androidx.compose.ui.graphics.Brush.horizontalGradient(
                                colors = listOf(
                                    NeuroColors.Primary.copy(alpha = 0.5f),
                                    NeuroColors.GlassAccent.copy(alpha = 0.6f)
                                )
                            ),
                            shape = RoundedCornerShape(20.dp)
                        )
                        .padding(horizontal = 16.dp, vertical = 10.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    // Animated typing indicator
                    val infiniteTransition = rememberInfiniteTransition(label = "typing")
                    val alpha by infiniteTransition.animateFloat(
                        initialValue = 0.3f,
                        targetValue = 1f,
                        animationSpec = infiniteRepeatable(
                            animation = tween(600, easing = LinearEasing),
                            repeatMode = RepeatMode.Reverse
                        ),
                        label = "alpha"
                    )

                    Box(
                        modifier = Modifier
                            .size(8.dp)
                            .background(NeuroColors.Primary.copy(alpha = alpha), CircleShape)
                    )
                    Spacer(modifier = Modifier.width(10.dp))
                    Text(
                        text = text,
                        color = NeuroColors.TextPrimary,
                        fontSize = 14.sp,
                        maxLines = 3,
                        overflow = androidx.compose.ui.text.style.TextOverflow.Ellipsis,
                        modifier = Modifier.weight(1f)
                    )
                }
            }
        }

        Row(
            verticalAlignment = Alignment.CenterVertically
        ) {
            // Attachment button
            IconButton(
                onClick = onAttachmentMenuToggle,
                modifier = Modifier.size(40.dp)
            ) {
                Icon(
                    Icons.Default.AttachFile,
                    contentDescription = "Attachment",
                    tint = NeuroColors.TextMuted
                )
            }

            Spacer(modifier = Modifier.width(4.dp))

            // Text input
            BasicTextField(
                value = text,
                onValueChange = onTextChange,
                modifier = Modifier
                    .weight(1f)
                    .height(48.dp)
                    .clip(RoundedCornerShape(24.dp))
                    .background(NeuroColors.GlassSecondary)
                    .padding(horizontal = 16.dp, vertical = 12.dp),
                textStyle = LocalTextStyle.current.copy(color = NeuroColors.TextPrimary),
                cursorBrush = SolidColor(NeuroColors.TextPrimary),
                keyboardOptions = KeyboardOptions(imeAction = ImeAction.Send),
                keyboardActions = KeyboardActions(onSend = { onSend() }),
                singleLine = true,
                decorationBox = { innerTextField ->
                    Box {
                        if (text.isEmpty()) {
                            Text(
                                text = "Ask Neuro anything...",
                                color = NeuroColors.TextMuted,
                                fontSize = 14.sp
                            )
                        }
                        innerTextField()
                    }
                }
            )

            Spacer(modifier = Modifier.width(8.dp))

            // Send or Mic button
            if (text.isNotBlank()) {
                // Send button
                IconButton(
                    onClick = onSend,
                    modifier = Modifier
                        .size(40.dp)
                        .background(NeuroColors.Primary, CircleShape)
                ) {
                    Icon(
                        Icons.AutoMirrored.Filled.Send,
                        contentDescription = "Send",
                        tint = NeuroColors.BackgroundDark
                    )
                }
            } else {
                // Mic button for voice message
                IconButton(
                    onClick = onVoiceClick,
                    modifier = Modifier.size(40.dp)
                ) {
                    Icon(
                        Icons.Default.Mic,
                        contentDescription = "Voice Message",
                        tint = NeuroColors.Primary
                    )
                }
            }
        }
    }
}

@Composable
fun ThinkingIndicator(agentName: String = "Neuro") {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .padding(8.dp),
        horizontalArrangement = Arrangement.Start
    ) {
        Row(
            modifier = Modifier
                .clip(RoundedCornerShape(16.dp))
                .background(NeuroColors.GlassAssistantBubble)
                .padding(horizontal = 16.dp, vertical = 12.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            repeat(3) { i ->
                Box(
                    modifier = Modifier
                        .size(8.dp)
                        .background(NeuroColors.TextMuted, CircleShape)
                        .padding(2.dp)
                )
                if (i < 2) Spacer(modifier = Modifier.width(4.dp))
            }
            Spacer(modifier = Modifier.width(8.dp))
            Text(
                text = "$agentName is thinking...",
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

    if (showCancelDialog) {
        AlertDialog(
            onDismissRequest = { showCancelDialog = false },
            title = { Text("Discard Recording?", color = Color.White) },
            text = { Text("Your voice message will be discarded.", color = Color.White) },
            confirmButton = {
                TextButton(onClick = {
                    showCancelDialog = false
                    onCancel()
                }) {
                    Text("Discard", color = NeuroColors.Error)
                }
            },
            dismissButton = {
                TextButton(onClick = { showCancelDialog = false }) {
                    Text("Keep", color = Color.White)
                }
            },
            containerColor = NeuroColors.BackgroundMid
        )
    }

    Column(
        modifier = Modifier
            .fillMaxWidth()
            .background(NeuroColors.BackgroundDark)
            .padding(horizontal = 16.dp, vertical = 12.dp)
            .padding(bottom = 24.dp)
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .height(60.dp)
                .clip(RoundedCornerShape(12.dp))
                .background(NeuroColors.GlassPrimary.copy(alpha = 0.3f))
                .padding(horizontal = 16.dp),
            horizontalArrangement = Arrangement.Center,
            verticalAlignment = Alignment.CenterVertically
        ) {
            val infiniteTransition = rememberInfiniteTransition(label = "waveform")
            
            repeat(20) { index ->
                val height by infiniteTransition.animateFloat(
                    initialValue = 20f,
                    targetValue = if (isPaused) 20f else 40f + (index % 3 * 10),
                    animationSpec = infiniteRepeatable(
                        animation = tween(
                            durationMillis = 300 + (index * 30),
                            easing = LinearEasing
                        ),
                        repeatMode = RepeatMode.Reverse
                    ),
                    label = "bar$index"
                )
                
                Box(
                    modifier = Modifier
                        .width(4.dp)
                        .height(height.dp)
                        .padding(horizontal = 1.dp)
                        .background(
                            if (isPaused) NeuroColors.TextMuted else NeuroColors.Primary,
                            RoundedCornerShape(2.dp)
                        )
                )
            }
        }

        Spacer(modifier = Modifier.height(12.dp))

        Text(
            text = if (isPaused) "Paused" else "Recording...",
            color = if (isPaused) NeuroColors.TextMuted else NeuroColors.Error,
            fontSize = 12.sp,
            modifier = Modifier.align(Alignment.CenterHorizontally)
        )

        Spacer(modifier = Modifier.height(12.dp))

        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceEvenly,
            verticalAlignment = Alignment.CenterVertically
        ) {
            IconButton(
                onClick = { showCancelDialog = true },
                modifier = Modifier
                    .size(48.dp)
                    .background(NeuroColors.GlassPrimary.copy(alpha = 0.3f), CircleShape)
            ) {
                Icon(
                    Icons.Default.Close,
                    contentDescription = "Cancel",
                    tint = NeuroColors.TextMuted,
                    modifier = Modifier.size(24.dp)
                )
            }

            IconButton(
                onClick = {
                    isPaused = !isPaused
                    if (isPaused) onPause() else onResume()
                },
                modifier = Modifier
                    .size(56.dp)
                    .background(NeuroColors.Primary.copy(alpha = 0.2f), CircleShape)
            ) {
                Icon(
                    if (isPaused) Icons.Default.PlayArrow else Icons.Default.Pause,
                    contentDescription = if (isPaused) "Resume" else "Pause",
                    tint = NeuroColors.Primary,
                    modifier = Modifier.size(28.dp)
                )
            }

            IconButton(
                onClick = onSend,
                modifier = Modifier
                    .size(48.dp)
                    .background(NeuroColors.Primary, CircleShape)
            ) {
                Icon(
                    Icons.AutoMirrored.Filled.Send,
                    contentDescription = "Send",
                    tint = Color.White,
                    modifier = Modifier.size(24.dp)
                )
            }
        }
    }
}
