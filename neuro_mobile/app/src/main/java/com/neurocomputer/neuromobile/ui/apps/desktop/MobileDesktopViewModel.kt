package com.neurocomputer.neuromobile.ui.apps.desktop

import android.content.Context
import androidx.compose.ui.geometry.Offset
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.neurocomputer.neuromobile.data.repository.BackendUrlRepository
import com.neurocomputer.neuromobile.data.service.LiveKitService
import dagger.hilt.android.lifecycle.HiltViewModel
import dagger.hilt.android.qualifiers.ApplicationContext
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import okhttp3.OkHttpClient
import okhttp3.Request
import org.json.JSONObject
import javax.inject.Inject

data class DesktopState(
    val isConnecting: Boolean = false,
    val isConnected: Boolean = false,
    val kioskActive: Boolean = false,
    val isTouchpadMode: Boolean = true,
    val isTabletMode: Boolean = false,
    val isKeyboardOpen: Boolean = false,
    val isVoiceTyping: Boolean = false,
    val isScrollMode: Boolean = false,
    val isClickMode: Boolean = false,
    val isFocusMode: Boolean = false,
    val toolbarOffset: Offset = Offset(16f, 200f),
    val localCursor: Offset = Offset(0.5f, 0.5f),
    val errorMessage: String? = null,
)

@HiltViewModel
class MobileDesktopViewModel @Inject constructor(
    @ApplicationContext private val context: Context,
    private val liveKitService: LiveKitService,
    private val backendUrlRepository: BackendUrlRepository,
    private val httpClient: OkHttpClient,
) : ViewModel() {

    private val _state = MutableStateFlow(DesktopState())
    val state: StateFlow<DesktopState> = _state.asStateFlow()

    val videoTrack = liveKitService.videoTrack
    val serverCursorPosition = liveKitService.serverCursorPosition
    val serverScreenDimensions = liveKitService.serverScreenDimensions

    init {
        viewModelScope.launch {
            liveKitService.state.collect { lkState ->
                _state.update { it.copy(
                    isConnected = lkState.connected,
                    kioskActive = if (!lkState.connected) false else it.kioskActive,
                ) }
            }
        }
    }

    fun connect() {
        viewModelScope.launch {
            _state.update { it.copy(isConnecting = true, errorMessage = null) }
            try {
                val baseUrl = backendUrlRepository.currentUrl.value
                val tokenUrl = "$baseUrl/livekit/token"
                val body = withContext(Dispatchers.IO) {
                    httpClient.newCall(Request.Builder().url(tokenUrl).build())
                        .execute()
                        .use { response ->
                            response.body?.string() ?: throw Exception("No token response")
                        }
                }
                val json = JSONObject(body)
                val token = json.getString("token")
                val url = json.optString("url", "wss://livekit.neurocomputer.io")
                val roomName = json.optString("room", "desktop")

                val success = liveKitService.connect(token = token, url = url, roomName = roomName)
                if (success) {
                    liveKitService.sendSession("mobile_connect")
                    _state.update { it.copy(kioskActive = true) }
                } else {
                    _state.update { it.copy(errorMessage = "Connection failed") }
                }
            } catch (e: Exception) {
                _state.update { it.copy(errorMessage = e.message ?: "Error") }
            } finally {
                _state.update { it.copy(isConnecting = false) }
            }
        }
    }

    fun disconnect() {
        liveKitService.sendSession("mobile_disconnect")
        liveKitService.disconnect()
        _state.update { it.copy(kioskActive = false) }
    }

    fun toggleTouchpadMode() = _state.update { it.copy(isTouchpadMode = !it.isTouchpadMode, isTabletMode = false) }
    fun toggleTabletMode()   = _state.update { it.copy(isTabletMode = !it.isTabletMode, isTouchpadMode = false) }
    fun toggleKeyboard()     = _state.update { it.copy(isKeyboardOpen = !it.isKeyboardOpen) }
    fun toggleVoiceTyping()  = _state.update { it.copy(isVoiceTyping = !it.isVoiceTyping) }
    fun toggleScrollMode()   = _state.update { it.copy(isScrollMode = !it.isScrollMode) }
    fun toggleClickMode()    = _state.update { it.copy(isClickMode = !it.isClickMode) }
    fun toggleFocusMode()    = _state.update { it.copy(isFocusMode = !it.isFocusMode) }
    fun setToolbarOffset(o: Offset) = _state.update { it.copy(toolbarOffset = o) }
    fun setLocalCursor(o: Offset)   = _state.update { it.copy(localCursor = o) }

    // LiveKit delegation methods
    fun sendDirectMove(x: Float, y: Float) = liveKitService.sendDirectMove(x, y)
    fun sendDirectClick(x: Float, y: Float, button: String, count: Int) = liveKitService.sendDirectClick(x, y, button, count)
    fun sendMouseScroll(dx: Float, dy: Float) = liveKitService.sendMouseScroll(dx, dy)
    fun sendKeyEvent(key: String) = liveKitService.sendKeyEvent(key)
    fun getLiveKitService(): LiveKitService = liveKitService
}
