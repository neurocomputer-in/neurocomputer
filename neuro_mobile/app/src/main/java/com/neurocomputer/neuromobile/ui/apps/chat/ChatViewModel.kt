package com.neurocomputer.neuromobile.ui.apps.chat

import android.content.Context
import android.media.MediaRecorder
import android.os.Build
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.neurocomputer.neuromobile.data.repository.BackendUrlRepository
import com.neurocomputer.neuromobile.data.service.ChatDataChannelService
import com.neurocomputer.neuromobile.data.service.ChatMessage
import com.neurocomputer.neuromobile.domain.model.Message
import dagger.assisted.Assisted
import dagger.assisted.AssistedFactory
import dagger.assisted.AssistedInject
import dagger.hilt.android.lifecycle.HiltViewModel
import dagger.hilt.android.qualifiers.ApplicationContext
import io.livekit.android.LiveKit
import io.livekit.android.RoomOptions
import io.livekit.android.events.RoomEvent
import io.livekit.android.events.collect
import io.livekit.android.room.Room
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.MultipartBody
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.asRequestBody
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONObject
import java.io.File
import java.util.UUID

data class LlmProviderInfo(
    val id: String,
    val name: String,
    val models: List<String>,
    val available: Boolean,
    val defaultModel: String,
)

data class ChatState(
    val messages: List<Message> = emptyList(),
    val inputText: String = "",
    val isLoading: Boolean = false,
    // LLM picker
    val llmProvider: String = "",
    val llmModel: String = "",
    val showLlmPicker: Boolean = false,
    val llmProviders: List<LlmProviderInfo> = emptyList(),
    // Voice message recording
    val isRecording: Boolean = false,
    val recordingSeconds: Int = 0,
    // Voice call
    val voiceCallActive: Boolean = false,
    val voiceCallConnecting: Boolean = false,
    val voiceCallMuted: Boolean = false,
    val voiceCallRoomName: String = "",
    val voiceInterimUser: String = "",
)

@HiltViewModel(assistedFactory = ChatViewModel.Factory::class)
class ChatViewModel @AssistedInject constructor(
    @Assisted("cid") val cid: String,
    @Assisted("agentId") val agentId: String,
    private val chatDataChannelService: ChatDataChannelService,
    private val httpClient: OkHttpClient,
    private val backendUrlRepository: BackendUrlRepository,
    @ApplicationContext private val context: Context,
) : ViewModel() {

    private val _state = MutableStateFlow(ChatState())
    val state: StateFlow<ChatState> = _state.asStateFlow()

    @AssistedFactory
    interface Factory {
        fun create(@Assisted("cid") cid: String, @Assisted("agentId") agentId: String): ChatViewModel
    }

    private var mediaRecorder: MediaRecorder? = null
    private var audioFile: File? = null
    private var recordingTimerJob: Job? = null
    private var voiceRoom: Room? = null

    init {
        observeMessages()
        connectIfNeeded()
        fetchCurrentLlm()
    }

    // ── Text chat ─────────────────────────────────────────────────────────────

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
                        val newMsg = Message(id = msg.messageId, text = msg.text, isUser = false)
                        _state.update { it.copy(messages = it.messages + newMsg, isLoading = false) }
                    }
                    is ChatMessage.VoiceMessage -> {
                        if (msg.sender == "user") return@collect
                        val newMsg = Message(id = msg.messageId, text = "", isUser = false, isVoice = true, audioUrl = msg.audioUrl)
                        _state.update { it.copy(messages = it.messages + newMsg, isLoading = false) }
                    }
                    is ChatMessage.SystemMessage -> Unit
                    else -> Unit
                }
            }
        }
    }

    fun onInputChange(text: String) = _state.update { it.copy(inputText = text) }

    fun send() {
        val text = _state.value.inputText.trim()
        if (text.isEmpty()) return
        val userMsg = Message(id = "user_${UUID.randomUUID()}", text = text, isUser = true)
        _state.update { it.copy(messages = it.messages + userMsg, inputText = "", isLoading = true) }

        viewModelScope.launch {
            val current = chatDataChannelService.connectionState.value
            if (!current.connected || current.conversationId != cid) {
                val connected = chatDataChannelService.connect(cid)
                if (!connected) {
                    _state.update {
                        it.copy(messages = it.messages + Message(id = "err_${UUID.randomUUID()}", text = "Failed to connect to chat", isUser = false), isLoading = false)
                    }
                    return@launch
                }
            }
            if (!chatDataChannelService.sendTextMessage(text)) {
                _state.update {
                    it.copy(messages = it.messages + Message(id = "err_${UUID.randomUUID()}", text = "Failed to send message", isUser = false), isLoading = false)
                }
            }
        }

        viewModelScope.launch {
            delay(45_000)
            if (_state.value.isLoading) _state.update { it.copy(isLoading = false) }
        }
    }

    // ── LLM picker ────────────────────────────────────────────────────────────

    fun openLlmPicker() {
        _state.update { it.copy(showLlmPicker = true) }
        if (_state.value.llmProviders.isEmpty()) loadProviders()
    }

    fun closeLlmPicker() = _state.update { it.copy(showLlmPicker = false) }

    fun updateLlmSettings(provider: String, model: String) {
        viewModelScope.launch {
            try {
                val baseUrl = backendUrlRepository.currentUrl.value
                val body = """{"provider":"$provider","model":"$model"}""".toRequestBody("application/json".toMediaType())
                withContext(Dispatchers.IO) {
                    httpClient.newCall(Request.Builder().url("$baseUrl/conversation/$cid/llm").patch(body).build()).execute().use { }
                }
                _state.update { it.copy(llmProvider = provider, llmModel = model, showLlmPicker = false) }
            } catch (e: Exception) {
                _state.update { it.copy(showLlmPicker = false) }
            }
        }
    }

    private fun fetchCurrentLlm() {
        viewModelScope.launch {
            try {
                val baseUrl = backendUrlRepository.currentUrl.value
                val body = withContext(Dispatchers.IO) {
                    httpClient.newCall(Request.Builder().url("$baseUrl/conversation/$cid/llm").build()).execute().use { it.body?.string() ?: "" }
                }
                val json = JSONObject(body)
                _state.update { it.copy(llmProvider = json.optString("provider", ""), llmModel = json.optString("model", "")) }
            } catch (_: Exception) { }
        }
    }

    private fun loadProviders() {
        viewModelScope.launch {
            try {
                val baseUrl = backendUrlRepository.currentUrl.value
                val body = withContext(Dispatchers.IO) {
                    httpClient.newCall(Request.Builder().url("$baseUrl/llm/providers").build()).execute().use { it.body?.string() ?: "" }
                }
                val json = JSONObject(body)
                val arr = json.getJSONArray("providers")
                val providers = (0 until arr.length()).map { i ->
                    val p = arr.getJSONObject(i)
                    val mArr = p.getJSONArray("models")
                    LlmProviderInfo(p.getString("id"), p.getString("name"), (0 until mArr.length()).map { mArr.getString(it) }, p.getBoolean("available"), p.getString("defaultModel"))
                }
                _state.update { it.copy(llmProviders = providers) }
            } catch (_: Exception) { }
        }
    }

    // ── Voice message (record → upload) ──────────────────────────────────────

    fun startRecording() {
        try {
            val file = File(context.cacheDir, "voice_${System.currentTimeMillis()}.m4a")
            audioFile = file
            @Suppress("DEPRECATION")
            mediaRecorder = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
                MediaRecorder(context)
            } else {
                MediaRecorder()
            }
            mediaRecorder!!.apply {
                setAudioSource(MediaRecorder.AudioSource.MIC)
                setOutputFormat(MediaRecorder.OutputFormat.MPEG_4)
                setAudioEncoder(MediaRecorder.AudioEncoder.AAC)
                setAudioSamplingRate(44100)
                setAudioEncodingBitRate(128000)
                setOutputFile(file.absolutePath)
                prepare()
                start()
            }
            _state.update { it.copy(isRecording = true, recordingSeconds = 0) }
            recordingTimerJob = viewModelScope.launch {
                while (true) {
                    delay(1000)
                    _state.update { it.copy(recordingSeconds = it.recordingSeconds + 1) }
                }
            }
        } catch (e: Exception) {
            releaseRecorder()
        }
    }

    fun cancelRecording() {
        releaseRecorder()
        audioFile?.delete()
        audioFile = null
        _state.update { it.copy(isRecording = false, recordingSeconds = 0) }
    }

    fun stopAndSendVoiceMessage() {
        recordingTimerJob?.cancel()
        recordingTimerJob = null
        try {
            mediaRecorder?.stop()
        } catch (_: Exception) { }
        releaseRecorder()

        val file = audioFile ?: run {
            _state.update { it.copy(isRecording = false, recordingSeconds = 0) }
            return
        }
        audioFile = null

        val tempId = "voice_${UUID.randomUUID()}"
        val placeholder = Message(id = tempId, text = "Transcribing…", isUser = true, isVoice = true)
        _state.update { it.copy(messages = it.messages + placeholder, isRecording = false, recordingSeconds = 0, isLoading = true) }

        viewModelScope.launch {
            try {
                val baseUrl = backendUrlRepository.currentUrl.value
                val requestBody = MultipartBody.Builder()
                    .setType(MultipartBody.FORM)
                    .addFormDataPart("file", "voice.m4a", file.asRequestBody("audio/m4a".toMediaType()))
                    .addFormDataPart("cid", cid)
                    .addFormDataPart("agent_id", agentId)
                    .build()
                val responseBody = withContext(Dispatchers.IO) {
                    httpClient.newCall(Request.Builder().url("$baseUrl/voice-message").post(requestBody).build()).execute().use { it.body?.string() ?: "" }
                }
                file.delete()
                val json = JSONObject(responseBody)
                val transcription = json.optString("transcription", "")
                val audioUrl = json.optString("audio_url", "")
                val updated = Message(id = tempId, text = transcription, isUser = true, isVoice = true, audioUrl = audioUrl)
                _state.update { it.copy(messages = it.messages.map { m -> if (m.id == tempId) updated else m }) }
            } catch (e: Exception) {
                file.delete()
                val errMsg = Message(id = "err_${UUID.randomUUID()}", text = "Voice send failed", isUser = false)
                _state.update { it.copy(messages = it.messages.filter { m -> m.id != tempId } + errMsg, isLoading = false) }
            }
        }
        // Safety timeout — clears spinner if AI response never arrives
        viewModelScope.launch {
            delay(60_000)
            if (_state.value.isLoading) _state.update { it.copy(isLoading = false) }
        }
    }

    private fun releaseRecorder() {
        recordingTimerJob?.cancel()
        recordingTimerJob = null
        try { mediaRecorder?.release() } catch (_: Exception) { }
        mediaRecorder = null
    }

    // ── Voice call (LiveKit) ──────────────────────────────────────────────────

    fun startVoiceCall() {
        if (_state.value.voiceCallActive || _state.value.voiceCallConnecting) return
        viewModelScope.launch {
            _state.update { it.copy(voiceCallConnecting = true) }
            try {
                val baseUrl = backendUrlRepository.currentUrl.value
                val reqBody = """{"conversation_id":"$cid","agent_id":"$agentId"}""".toRequestBody("application/json".toMediaType())
                val responseBody = withContext(Dispatchers.IO) {
                    httpClient.newCall(Request.Builder().url("$baseUrl/voice/call").post(reqBody).build()).execute().use { it.body?.string() ?: "" }
                }
                val json = JSONObject(responseBody)
                val token = json.getString("token")
                val url = json.getString("url")
                val roomName = json.optString("room_name", cid)

                val room = LiveKit.create(appContext = context, options = RoomOptions(adaptiveStream = false, dynacast = false))
                voiceRoom = room

                // Listen for data channel events (transcripts, state)
                viewModelScope.launch {
                    room.events.collect { event ->
                        if (event is RoomEvent.DataReceived) {
                            handleVoiceData(event.topic ?: "", event.data)
                        }
                    }
                }

                room.connect(url, token)
                room.localParticipant.setMicrophoneEnabled(true)

                _state.update { it.copy(voiceCallActive = true, voiceCallConnecting = false, voiceCallRoomName = roomName) }
            } catch (e: Exception) {
                voiceRoom = null
                _state.update { it.copy(voiceCallConnecting = false) }
            }
        }
    }

    fun endVoiceCall() {
        viewModelScope.launch {
            val room = voiceRoom
            voiceRoom = null
            try { room?.disconnect() } catch (_: Exception) { }
            val baseUrl = backendUrlRepository.currentUrl.value
            try {
                val body = """{"conversation_id":"$cid"}""".toRequestBody("application/json".toMediaType())
                withContext(Dispatchers.IO) {
                    httpClient.newCall(Request.Builder().url("$baseUrl/voice/hangup").post(body).build()).execute().use { }
                }
            } catch (_: Exception) { }
            _state.update { it.copy(voiceCallActive = false, voiceCallMuted = false, voiceCallRoomName = "", voiceInterimUser = "") }
        }
    }

    private fun handleVoiceData(topic: String, data: ByteArray) {
        try {
            val text = data.toString(Charsets.UTF_8)
            val parsed = JSONObject(text)
            when (topic) {
                "voice.user_transcript" -> {
                    val isFinal = parsed.optBoolean("is_final", false)
                    val msgText = parsed.optString("text", "")
                    if (isFinal && msgText.isNotEmpty()) {
                        val msg = Message(
                            id = parsed.optString("message_id", "voice-user-${System.currentTimeMillis()}"),
                            text = msgText,
                            isUser = true,
                            isVoice = true,
                        )
                        _state.update { it.copy(messages = it.messages + msg, voiceInterimUser = "", isLoading = true) }
                    } else if (msgText.isNotEmpty()) {
                        _state.update { it.copy(voiceInterimUser = msgText) }
                    }
                }
                "voice.agent_transcript" -> {
                    val done = parsed.optBoolean("done", false)
                    val msgText = parsed.optString("text", "")
                    if (done && msgText.isNotEmpty()) {
                        val msg = Message(
                            id = parsed.optString("message_id", "voice-agent-${System.currentTimeMillis()}"),
                            text = msgText,
                            isUser = false,
                            isVoice = true,
                        )
                        _state.update { it.copy(messages = it.messages + msg, isLoading = false) }
                    }
                }
                else -> { }
            }
        } catch (_: Exception) { }
    }

    fun toggleVoiceMute() {
        val newMuted = !_state.value.voiceCallMuted
        viewModelScope.launch {
            try { voiceRoom?.localParticipant?.setMicrophoneEnabled(!newMuted) } catch (_: Exception) { }
        }
        _state.update { it.copy(voiceCallMuted = newMuted) }
    }

    override fun onCleared() {
        super.onCleared()
        cancelRecording()
        viewModelScope.launch { try { voiceRoom?.disconnect() } catch (_: Exception) { } }
    }
}
