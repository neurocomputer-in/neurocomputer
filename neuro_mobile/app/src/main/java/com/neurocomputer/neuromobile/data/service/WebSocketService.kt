package com.neurocomputer.neuromobile.data.service

import com.neurocomputer.neuromobile.data.repository.BackendUrlRepository
import io.ktor.client.*
import io.ktor.client.engine.okhttp.*
import io.ktor.client.plugins.websocket.*
import io.ktor.websocket.*
import kotlinx.coroutines.*
import kotlinx.coroutines.flow.*
import kotlinx.serialization.json.*
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import java.util.concurrent.TimeUnit
import javax.inject.Inject
import javax.inject.Singleton

sealed class WsMessage {
    data class Text(val text: String) : WsMessage()
    data class Json(val topic: String, val data: String, val origin: String? = null) : WsMessage()
    data object Connected : WsMessage()
    data object Disconnected : WsMessage()
    data class Error(val error: String) : WsMessage()
}

@Singleton
class WebSocketService @Inject constructor(
    private val backendUrlRepository: BackendUrlRepository
) {
    private val _messages = MutableSharedFlow<WsMessage>(replay = 0, extraBufferCapacity = 64)
    val messages: SharedFlow<WsMessage> = _messages.asSharedFlow()

    private val _connectionState = MutableStateFlow(false)
    val connectionState: StateFlow<Boolean> = _connectionState.asStateFlow()

    private val _pendingMessageOrigin = MutableStateFlow<String?>(null)
    val pendingMessageOrigin: StateFlow<String?> = _pendingMessageOrigin.asStateFlow()

    private var session: WebSocketSession? = null
    private var conversationId: String? = null
    private var reconnectJob: Job? = null
    private val scope = CoroutineScope(Dispatchers.IO + SupervisorJob())

    private val httpClient = HttpClient(OkHttp) {
        install(WebSockets)
    }

    private val chatClient = OkHttpClient.Builder()
        .connectTimeout(10, TimeUnit.SECONDS)
        .readTimeout(30, TimeUnit.SECONDS)
        .writeTimeout(10, TimeUnit.SECONDS)
        .build()

    private val json = Json { ignoreUnknownKeys = true }

    fun markMessageOrigin(origin: String) {
        android.util.Log.d("WSS", "markMessageOrigin: setting to $origin, current=${_pendingMessageOrigin.value}")
        _pendingMessageOrigin.value = origin
        android.util.Log.d("WSS", "markMessageOrigin: confirmed = ${_pendingMessageOrigin.value}")
    }

    fun connect(conversationId: String) {
        this.conversationId = conversationId
        reconnectJob?.cancel()
        reconnectJob = scope.launch {
            doConnect()
        }
    }

    fun reconnectTo(cid: String) {
        conversationId = cid
        reconnectJob?.cancel()
        reconnectJob = scope.launch {
            doConnect()
        }
    }

    private suspend fun doConnect() {
        try {
            val wsBaseUrl = backendUrlRepository.wsUrl.value
            val url = "$wsBaseUrl/$conversationId"
            _connectionState.value = false

            session?.close()
            session = null

            httpClient.webSocket(url) {
                session = this
                _connectionState.value = true
                _messages.emit(WsMessage.Connected)

                try {
                    for (frame in incoming) {
                        when (frame) {
                            is Frame.Text -> {
                                val text = frame.readText()
                                parseAndEmit(text)
                            }
                            is Frame.Close -> {
                                _messages.emit(WsMessage.Disconnected)
                            }
                            else -> {}
                        }
                    }
                } catch (e: Exception) {
                    _messages.emit(WsMessage.Error(e.message ?: "WebSocket error"))
                }
            }
        } catch (e: Exception) {
            _connectionState.value = false
            _messages.emit(WsMessage.Error(e.message ?: "Connection failed"))
            scheduleReconnect()
        }
    }

    private suspend fun parseAndEmit(text: String) {
        val origin = _pendingMessageOrigin.value
        android.util.Log.d("WSS", "parseAndEmit: read origin=$origin, pendingBeforeClear=${_pendingMessageOrigin.value}")
        _pendingMessageOrigin.value = null
        android.util.Log.d("WSS", "parseAndEmit: cleared, now=${_pendingMessageOrigin.value}")
        try {
            val jsonMap = json.parseToJsonElement(text).jsonObject
            val topic = jsonMap["topic"]?.jsonPrimitive?.content
                ?: jsonMap["type"]?.jsonPrimitive?.content
                ?: "unknown"
            val data = jsonMap["data"]?.jsonPrimitive?.content
                ?: jsonMap["text"]?.jsonPrimitive?.content
                ?: text
            if (origin != null) {
                _messages.emit(WsMessage.Json(topic, data, origin))
            } else {
                _messages.emit(WsMessage.Json(topic, data))
            }
        } catch (e: Exception) {
            // Not JSON or unexpected structure - emit raw text
            _messages.emit(WsMessage.Text(text))
        }
    }

    private fun scheduleReconnect() {
        scope.launch {
            delay(3000)
            if (conversationId != null) {
                doConnect()
            }
        }
    }

    suspend fun sendMessage(text: String, cid: String? = null): Result<Unit> {
        val conversationIdToUse = cid ?: conversationId ?: return Result.failure(Exception("Not connected"))

        return withContext(Dispatchers.IO) {
            try {
                val baseUrl = backendUrlRepository.currentUrl.value
                val body = """{"cid":"$conversationIdToUse","text":"$text"}"""
                val requestBody = body.toRequestBody("application/json".toMediaType())
                val request = Request.Builder()
                    .url("$baseUrl/chat")
                    .post(requestBody)
                    .build()

                val resp = chatClient.newCall(request).execute()
                if (resp.isSuccessful) {
                    resp.close()
                    Result.success(Unit)
                } else {
                    resp.close()
                    Result.failure(Exception("HTTP ${resp.code}"))
                }
            } catch (e: Exception) {
                Result.failure(e)
            }
        }
    }

    fun disconnect() {
        reconnectJob?.cancel()
        conversationId = null
        scope.launch {
            session?.close()
            session = null
            _connectionState.value = false
        }
    }

    fun close() {
        disconnect()
        scope.cancel()
        httpClient.close()
    }
}
