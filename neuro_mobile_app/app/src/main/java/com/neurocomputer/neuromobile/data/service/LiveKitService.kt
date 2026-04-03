package com.neurocomputer.neuromobile.data.service

import android.content.Context
import com.neurocomputer.neuromobile.data.repository.BackendUrlRepository
import io.livekit.android.LiveKit
import io.livekit.android.RoomOptions
import io.livekit.android.events.RoomEvent
import io.livekit.android.events.collect
import io.livekit.android.room.Room
import io.livekit.android.room.track.VideoTrack
import io.livekit.android.room.track.Track
import io.livekit.android.room.track.TrackPublication
import io.livekit.android.room.participant.Participant
import io.livekit.android.room.track.DataPublishReliability
import io.livekit.android.util.LoggingLevel
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import kotlinx.serialization.Serializable
import kotlinx.serialization.encodeToString
import kotlinx.serialization.json.Json
import javax.inject.Inject
import javax.inject.Singleton
import dagger.hilt.android.qualifiers.ApplicationContext

data class LiveKitState(
    val connected: Boolean = false,
    val screenSharing: Boolean = false,
    val roomName: String = ""
)

@Serializable
data class MouseEvent(
    val type: String,
    val dx: Float = 0f,
    val dy: Float = 0f,
    val x: Float = 0f,
    val y: Float = 0f,
    val deltaX: Float = 0f,
    val deltaY: Float = 0f,
    val button: String = "left",
    val key: String = "",
    val count: Int = 1,
    val modifiers: List<String> = emptyList()
)

@Singleton
class LiveKitService @Inject constructor(
    @ApplicationContext private val context: Context,
    private val backendUrlRepository: BackendUrlRepository
) {
    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.Main)
    
    private val _currentRoom = MutableStateFlow<Room?>(null)
    val currentRoom: StateFlow<Room?> = _currentRoom.asStateFlow()
    
    private var room: Room?
        get() = _currentRoom.value
        set(value) {
            _currentRoom.value = value
        }

    private val _state = MutableStateFlow(LiveKitState())
    val state: StateFlow<LiveKitState> = _state.asStateFlow()

    private val _videoTrack = MutableStateFlow<VideoTrack?>(null)
    val videoTrack: StateFlow<VideoTrack?> = _videoTrack.asStateFlow()

    private val json = Json { ignoreUnknownKeys = true }

    suspend fun connect(token: String, url: String, roomName: String): Boolean {
        return try {
            // If already connected to a different room, disconnect first
            if (room?.state == Room.State.CONNECTED && _state.value.roomName != roomName) {
                disconnect()
            }

            if (room == null) {
                room = LiveKit.create(
                    appContext = context,
                    options = RoomOptions(
                        adaptiveStream = true,
                        dynacast = true
                    )
                )
            }

            val currentRoom = room!!
            
            // Set up event collection
            scope.launch {
                currentRoom.events.collect { event ->
                    when (event) {
                        is RoomEvent.TrackSubscribed -> {
                            if (event.track is VideoTrack) {
                                _videoTrack.value = event.track as VideoTrack
                                _state.value = _state.value.copy(screenSharing = true)
                            }
                        }
                        is RoomEvent.TrackUnsubscribed -> {
                            if (event.track is VideoTrack) {
                                _videoTrack.value = null
                                _state.value = _state.value.copy(screenSharing = false)
                            }
                        }
                        is RoomEvent.Disconnected -> {
                            _state.value = LiveKitState()
                            _videoTrack.value = null
                        }
                        else -> {}
                    }
                }
            }

            currentRoom.connect(url, token)
            _state.value = _state.value.copy(connected = true, roomName = roomName)
            true
        } catch (e: Exception) {
            e.printStackTrace()
            false
        }
    }

    fun disconnect() {
        scope.launch {
            room?.disconnect()
            _state.value = LiveKitState()
            _videoTrack.value = null
        }
    }

    fun sendMouseEvent(event: MouseEvent) {
        scope.launch(Dispatchers.IO) {
            try {
                val currentRoom = room ?: return@launch
                if (currentRoom.state != Room.State.CONNECTED) return@launch

                val payload = json.encodeToString(event)
                val data = payload.toByteArray(Charsets.UTF_8)

                val reliability = if (event.type == "mouse_move" || event.type == "scroll") {
                    DataPublishReliability.LOSSY
                } else {
                    DataPublishReliability.RELIABLE
                }

                currentRoom.localParticipant.publishData(
                    data = data,
                    reliability = reliability,
                    topic = "mouse_control"
                )
            } catch (e: Exception) {
                e.printStackTrace()
            }
        }
    }

    fun sendKeyEvent(key: String, modifiers: List<String> = emptyList()) {
        sendMouseEvent(MouseEvent(type = "key", key = key, modifiers = modifiers))
    }

    fun sendMouseMove(dx: Float, dy: Float) {
        sendMouseEvent(MouseEvent(type = "mouse_move", dx = dx, dy = dy))
    }

    fun sendMouseClick(x: Float, y: Float, button: String = "left") {
        sendMouseEvent(MouseEvent(type = "click", x = x, y = y, button = button))
    }

    fun sendMouseScroll(dx: Float, dy: Float) {
        sendMouseEvent(MouseEvent(type = "scroll", deltaX = dx, deltaY = dy))
    }

    fun sendAction(type: String, button: String = "left", count: Int = 1) {
        sendMouseEvent(MouseEvent(type = type, button = button, count = count))
    }
}
