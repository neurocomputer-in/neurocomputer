package com.neurocomputer.neuromobile.data.service

import com.neurocomputer.neuromobile.data.repository.BackendUrlRepository
import io.ktor.client.HttpClient
import io.ktor.client.engine.okhttp.OkHttp
import io.ktor.client.plugins.websocket.WebSockets
import io.ktor.client.plugins.websocket.webSocket
import io.ktor.websocket.Frame
import io.ktor.websocket.WebSocketSession
import io.ktor.websocket.close
import io.ktor.websocket.readBytes
import io.ktor.websocket.readReason
import io.ktor.websocket.readText
import io.ktor.websocket.send
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.cancel
import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharedFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asSharedFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.buildJsonObject
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive
import kotlinx.serialization.json.put
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONObject
import javax.inject.Inject

/**
 * Per-tab terminal WebSocket lifecycle:
 *   1. POST /terminal → server creates conversation file + tmux session, returns backend cid
 *   2. Open WS /terminal/ws/{backendCid} (binary protocol)
 *   3. Inbound: Frame.Binary = raw PTY stdout, Frame.Text = JSON control (ready/exit/error)
 *   4. Outbound: Frame.Binary = stdin, Frame.Text = JSON control (resize/ping)
 *
 * NOT a singleton — each ViewModel owns its own instance.
 */
sealed class TerminalEvent {
    data class Bytes(val data: ByteArray) : TerminalEvent()
    data object Ready : TerminalEvent()
    data class Exit(val code: Int) : TerminalEvent()
    data class Error(val msg: String) : TerminalEvent()
    data object Disconnected : TerminalEvent()
}

class TerminalWsService @Inject constructor(
    private val backendUrlRepository: BackendUrlRepository,
    private val httpClient: OkHttpClient,
) {
    private val _events = MutableSharedFlow<TerminalEvent>(replay = 0, extraBufferCapacity = 64)
    val events: SharedFlow<TerminalEvent> = _events.asSharedFlow()

    private val _ready = MutableStateFlow(false)
    val ready: StateFlow<Boolean> = _ready.asStateFlow()

    private val scope = CoroutineScope(Dispatchers.IO + SupervisorJob())
    private var session: WebSocketSession? = null
    private var wsJob: Job? = null
    private var backendCid: String? = null
    // Latched true on close() so the reconnect loop stops; otherwise any WS
    // disconnect (network blip, server restart, idle timeout) gets reconnected
    // automatically without re-creating the tmux session.
    private var explicitlyClosed: Boolean = false
    // Reset to base when a connection completes the handshake; bumps on each
    // failed attempt so we don't hammer the server during outage.
    @Volatile private var reconnectBackoffMs: Long = BASE_BACKOFF_MS
    // Cached last-requested geometry. The TerminalView lays out before the WS
    // handshake completes, so the first resize() arrives with no socket. We
    // replay it as soon as the socket opens — otherwise tmux/the shell stay
    // sized to whatever the prior attach left them at, leaving large blank
    // regions in the view.
    private var pendingCols: Int = 0
    private var pendingRows: Int = 0

    private val ktor = HttpClient(OkHttp) { install(WebSockets) }

    /** Creates a backend session (POST /terminal) then opens WS. On disconnect,
     *  the loop reconnects to the SAME backend cid — tmux survives across WS
     *  drops, so reusing the cid keeps the user's session/history intact.
     *  Idempotent. */
    fun start() {
        if (wsJob != null) return
        explicitlyClosed = false
        wsJob = scope.launch {
            val cid = backendCid ?: createSession()?.also { backendCid = it } ?: run {
                _events.emit(TerminalEvent.Error("Failed to create terminal session"))
                return@launch
            }
            // Reconnect loop with mild backoff. The tmux session is server-side
            // and persists, so each reconnect re-attaches and the emulator
            // gets a fresh paint of current screen state.
            while (!explicitlyClosed) {
                connectWs(cid)
                if (explicitlyClosed) break
                kotlinx.coroutines.delay(reconnectBackoffMs)
                reconnectBackoffMs = (reconnectBackoffMs * 2).coerceAtMost(MAX_BACKOFF_MS)
            }
        }
    }

    private fun createSession(): String? {
        return try {
            val baseUrl = backendUrlRepository.currentUrl.value
            val body = """{"title":"terminal"}""".toRequestBody("application/json".toMediaType())
            val resp = httpClient.newCall(
                Request.Builder().url("$baseUrl/terminal").post(body).build()
            ).execute()
            resp.use {
                if (!it.isSuccessful) return null
                val json = JSONObject(it.body?.string() ?: return null)
                json.optString("cid", "").ifEmpty { null }
            }
        } catch (e: Exception) {
            null
        }
    }

    private suspend fun connectWs(cid: String) {
        try {
            val wsBase = backendUrlRepository.currentUrl.value
                .replace("http://", "ws://")
                .replace("https://", "wss://")
            val url = "$wsBase/terminal/ws/$cid"
            ktor.webSocket(url) {
                session = this
                try {
                    for (frame in incoming) {
                        when (frame) {
                            is Frame.Binary -> _events.emit(TerminalEvent.Bytes(frame.readBytes()))
                            is Frame.Text -> handleControl(frame.readText())
                            is Frame.Close -> {
                                _events.emit(TerminalEvent.Disconnected)
                                _ready.value = false
                            }
                            else -> {}
                        }
                    }
                } catch (e: Exception) {
                    _events.emit(TerminalEvent.Error(e.message ?: "ws read error"))
                }
            }
        } catch (e: Exception) {
            _events.emit(TerminalEvent.Error(e.message ?: "ws connect failed"))
        } finally {
            session = null
            _ready.value = false
        }
    }

    private suspend fun handleControl(raw: String) {
        try {
            val obj = Json.parseToJsonElement(raw).jsonObject
            when (obj["type"]?.jsonPrimitive?.content) {
                "ready" -> {
                    _ready.value = true
                    // Successful handshake — reconnect loop should start from
                    // the base delay if the next disconnect happens.
                    reconnectBackoffMs = BASE_BACKOFF_MS
                    _events.emit(TerminalEvent.Ready)
                    if (pendingCols > 0 && pendingRows > 0) resize(pendingCols, pendingRows)
                }
                "exit" -> {
                    val code = obj["code"]?.jsonPrimitive?.content?.toIntOrNull() ?: 0
                    _events.emit(TerminalEvent.Exit(code))
                }
                "error" -> {
                    val msg = obj["msg"]?.jsonPrimitive?.content ?: "error"
                    _events.emit(TerminalEvent.Error(msg))
                }
                else -> {}
            }
        } catch (_: Exception) {}
    }

    /** Send raw stdin bytes (UTF-8 encoded). Caller appends \n for Enter. */
    fun sendInput(text: String) {
        val s = session ?: return
        scope.launch {
            try { s.send(Frame.Binary(true, text.toByteArray(Charsets.UTF_8))) } catch (_: Exception) {}
        }
    }

    /** Send a slice of raw stdin bytes — used by the terminal emulator's keystroke pipeline. */
    fun sendBytes(data: ByteArray, offset: Int, count: Int) {
        val s = session ?: return
        val payload = data.copyOfRange(offset, offset + count)
        scope.launch {
            try { s.send(Frame.Binary(true, payload)) } catch (_: Exception) {}
        }
    }

    fun resize(cols: Int, rows: Int) {
        pendingCols = cols
        pendingRows = rows
        val s = session ?: return
        scope.launch {
            try {
                val payload = buildJsonObject {
                    put("type", "resize"); put("cols", cols); put("rows", rows)
                }.toString()
                s.send(Frame.Text(payload))
            } catch (_: Exception) {}
        }
    }

    fun close() {
        explicitlyClosed = true
        wsJob?.cancel()
        wsJob = null
        scope.launch {
            try { session?.close() } catch (_: Exception) {}
            session = null
        }
    }

    companion object {
        private const val BASE_BACKOFF_MS = 500L
        private const val MAX_BACKOFF_MS = 5_000L
    }
}
