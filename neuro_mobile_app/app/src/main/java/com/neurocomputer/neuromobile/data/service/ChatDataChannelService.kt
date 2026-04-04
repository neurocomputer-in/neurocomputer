package com.neurocomputer.neuromobile.data.service

import android.content.Context
import android.util.Log
import com.neurocomputer.neuromobile.data.repository.BackendUrlRepository
import io.livekit.android.LiveKit
import io.livekit.android.RoomOptions
import io.livekit.android.events.RoomEvent
import io.livekit.android.events.collect
import io.livekit.android.room.Room
import io.livekit.android.room.participant.LocalParticipant
import io.livekit.android.room.track.DataPublishReliability
import io.livekit.android.util.LoggingLevel
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharedFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asSharedFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import kotlinx.serialization.Serializable
import kotlinx.serialization.SerialName
import kotlinx.serialization.encodeToString
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import java.util.concurrent.TimeUnit
import javax.inject.Inject
import javax.inject.Singleton
import dagger.hilt.android.qualifiers.ApplicationContext

sealed class ChatMessage {
    abstract val messageId: String
    abstract val sender: String
    abstract val timestamp: String

    @Serializable
    data class TextMessage(
        @SerialName("message_id") override val messageId: String,
        @SerialName("sender") override val sender: String,
        @SerialName("timestamp") override val timestamp: String,
        @SerialName("text") val text: String,
        @SerialName("type") val type: String = "text",
        @SerialName("origin") val origin: String? = null
    ) : ChatMessage()

    @Serializable
    data class VoiceMessage(
        @SerialName("message_id") override val messageId: String,
        @SerialName("sender") override val sender: String,
        @SerialName("timestamp") override val timestamp: String,
        @SerialName("audio_url") val audioUrl: String = "",
        @SerialName("duration_ms") val durationMs: Int = 0,
        @SerialName("type") val type: String = "voice",
        @SerialName("origin") val origin: String? = null
    ) : ChatMessage()

    @Serializable
    data class OcrMessage(
        @SerialName("message_id") override val messageId: String,
        @SerialName("sender") override val sender: String,
        @SerialName("timestamp") override val timestamp: String,
        @SerialName("text") val text: String,
        @SerialName("type") val type: String = "ocr",
        @SerialName("origin") val origin: String? = null
    ) : ChatMessage()

    @Serializable
    data class TypingIndicator(
        override val messageId: String = "",
        override val sender: String = "",
        override val timestamp: String = "",
        @SerialName("is_typing") val isTyping: Boolean = false,
        @SerialName("type") val type: String = "typing"
    ) : ChatMessage()

    @Serializable
    data class SystemMessage(
        @SerialName("message_id") override val messageId: String,
        @SerialName("sender") override val sender: String = "system",
        @SerialName("timestamp") override val timestamp: String,
        @SerialName("topic") val topic: String,
        @SerialName("metadata") val metadata: JsonObject? = null,
        @SerialName("type") val type: String = "system"
    ) : ChatMessage()
}

data class ChatConnectionState(
    val connected: Boolean = false,
    val roomName: String = "",
    val conversationId: String = ""
)

@Singleton
class ChatDataChannelService @Inject constructor(
    @ApplicationContext private val context: Context,
    private val backendUrlRepository: BackendUrlRepository
) {
    companion object {
        private const val TAG = "ChatDataChannel"
        private const val TOPIC_CHAT_MESSAGE = "chat_message"
        private const val TOPIC_AGENT_RESPONSE = "agent_response"
        private const val TOPIC_OCR_MESSAGE = "ocr_message"
        private const val TOPIC_SYSTEM_EVENT = "system_event"
    }

    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.Main)

    private var room: Room? = null
    private var localParticipant: LocalParticipant? = null

    private val _connectionState = MutableStateFlow(ChatConnectionState())
    val connectionState: StateFlow<ChatConnectionState> = _connectionState.asStateFlow()

    private val _messages = MutableSharedFlow<ChatMessage>(replay = 5, extraBufferCapacity = 64)
    val messages: SharedFlow<ChatMessage> = _messages.asSharedFlow()

    private val _connectionError = MutableSharedFlow<String>(replay = 0)
    val connectionError: SharedFlow<String> = _connectionError.asSharedFlow()

    private val json = Json { 
        ignoreUnknownKeys = true 
        encodeDefaults = true
    }

    private val httpClient = OkHttpClient.Builder()
        .connectTimeout(10, TimeUnit.SECONDS)
        .readTimeout(30, TimeUnit.SECONDS)
        .writeTimeout(10, TimeUnit.SECONDS)
        .build()

    suspend fun connect(conversationId: String): Boolean {
        return try {
            Log.d(TAG, "Connecting to chat room: $conversationId")

            // Check if already connected to the correct room
            if (room?.state == Room.State.CONNECTED && _connectionState.value.conversationId == conversationId) {
                Log.d(TAG, "Already connected to this conversation")
                return true
            }

            // Disconnect if different room or not connected
            if (room != null && _connectionState.value.conversationId != conversationId) {
                Log.d(TAG, "Different conversation, disconnecting first")
                disconnect()
            }

            val tokenData = getChatToken(conversationId)
            if (tokenData == null) {
                Log.e(TAG, "Failed to get chat token")
                _connectionError.emit("Failed to get chat token")
                return false
            }

            val token = tokenData["token"] as? String ?: return false
            val url = tokenData["url"] as? String ?: return false
            val roomName = tokenData["room_name"] as? String ?: return false

            room = LiveKit.create(
                appContext = context,
                options = RoomOptions(
                    adaptiveStream = true,
                    dynacast = true
                )
            )

            localParticipant = room?.localParticipant

            setupRoomEventListeners()

            Log.d(TAG, "Calling room.connect()...")
            room?.connect(url, token)
            Log.d(TAG, "room.connect() called, state: ${room?.state}")

            // Wait for connection to establish
            var attempts = 0
            while (room?.state != Room.State.CONNECTED && attempts < 10) {
                kotlinx.coroutines.delay(200)
                attempts++
                Log.d(TAG, "Waiting for connection... attempt $attempts, state: ${room?.state}")
            }

            if (room?.state != Room.State.CONNECTED) {
                Log.e(TAG, "Room not connected after waiting, state: ${room?.state}")
            }

            _connectionState.value = ChatConnectionState(
                connected = room?.state == Room.State.CONNECTED,
                roomName = roomName,
                conversationId = conversationId
            )

            Log.d(TAG, "Connected to chat room: $roomName, state: ${room?.state}")
            true
        } catch (e: Exception) {
            Log.e(TAG, "Error connecting to chat room", e)
            _connectionError.emit(e.message ?: "Connection failed")
            false
        }
    }

    private fun setupRoomEventListeners() {
        val currentRoom = room ?: return

        scope.launch {
            currentRoom.events.collect { event ->
                when (event) {
                    is RoomEvent.DataReceived -> {
                        val topic = event.topic ?: "unknown"
                        Log.d(TAG, "DataReceived event: topic='$topic', data size=${event.data.size}")
                        handleDataReceived(topic, event.data)
                    }
                    is RoomEvent.Disconnected -> {
                        Log.d(TAG, "Disconnected from chat room")
                        _connectionState.value = ChatConnectionState()
                    }
                    is RoomEvent.TrackSubscribed -> {
                        Log.d(TAG, "Track subscribed: ${event.track.sid}")
                    }
                    is RoomEvent.TrackUnsubscribed -> {
                        Log.d(TAG, "Track unsubscribed: ${event.track.sid}")
                    }
                    is RoomEvent.Connected -> {
                        Log.d(TAG, "RoomEvent.Connected received")
                    }
                    is RoomEvent.Reconnecting -> {
                        Log.d(TAG, "RoomEvent.Reconnecting")
                    }
                    else -> {
                        Log.d(TAG, "Other room event: ${event::class.simpleName}")
                    }
                }
            }
        }
    }

    private fun handleDataReceived(topic: String, data: ByteArray) {
        try {
            val jsonString = data.toString(Charsets.UTF_8)
            Log.d(TAG, "handleDataReceived: topic='$topic', data=${jsonString.take(100)}")

            val message = when (topic) {
                TOPIC_CHAT_MESSAGE, TOPIC_AGENT_RESPONSE -> {
                    Log.d(TAG, "Decoding TextMessage from: $jsonString")
                    json.decodeFromString<ChatMessage.TextMessage>(jsonString)
                }
                TOPIC_OCR_MESSAGE -> {
                    Log.d(TAG, "Decoding OcrMessage from: $jsonString")
                    json.decodeFromString<ChatMessage.OcrMessage>(jsonString)
                }
                TOPIC_SYSTEM_EVENT -> {
                    Log.d(TAG, "Decoding SystemMessage from: $jsonString")
                    json.decodeFromString<ChatMessage.SystemMessage>(jsonString)
                }
                else -> {
                    Log.w(TAG, "Unknown topic: $topic, ignoring")
                    return
                }
            }

            Log.d(TAG, "Emitting message to SharedFlow: ${message.messageId}")
            scope.launch {
                _messages.emit(message)
            }
        } catch (e: Exception) {
            Log.e(TAG, "Error parsing message", e)
        }
    }

    suspend fun sendOcrMessage(ocrText: String, origin: String = "app"): Boolean {
        val currentRoom = room
        val participant = localParticipant

        if (currentRoom == null || participant == null) {
            Log.e(TAG, "Not connected to chat room")
            return false
        }

        if (currentRoom.state != Room.State.CONNECTED) {
            Log.e(TAG, "Room not connected")
            return false
        }

        return try {
            val message = ChatMessage.OcrMessage(
                messageId = "ocr_${System.currentTimeMillis()}",
                sender = "user",
                timestamp = System.currentTimeMillis().toString(),
                text = ocrText,
                origin = origin
            )

            val payload = json.encodeToString(message)
            val data = payload.toByteArray(Charsets.UTF_8)

            participant.publishData(
                data = data,
                reliability = DataPublishReliability.RELIABLE,
                topic = TOPIC_OCR_MESSAGE
            )

            Log.d(TAG, "Sent OCR message: ${ocrText.take(50)}")
            true
        } catch (e: Exception) {
            Log.e(TAG, "Error sending OCR message", e)
            false
        }
    }

    suspend fun sendTextMessage(text: String, origin: String = "app"): Boolean {
        val currentRoom = room
        val participant = localParticipant

        if (currentRoom == null || participant == null) {
            Log.e(TAG, "Not connected to chat room")
            return false
        }

        if (currentRoom.state != Room.State.CONNECTED) {
            Log.e(TAG, "Room not connected")
            return false
        }

        return try {
            val message = ChatMessage.TextMessage(
                messageId = "msg_${System.currentTimeMillis()}",
                sender = "user",
                timestamp = System.currentTimeMillis().toString(),
                text = text,
                origin = origin
            )

            val payload = json.encodeToString(message)
            val data = payload.toByteArray(Charsets.UTF_8)

            participant.publishData(
                data = data,
                reliability = DataPublishReliability.RELIABLE,
                topic = TOPIC_CHAT_MESSAGE
            )

            Log.d(TAG, "Sent message: ${text.take(50)}")
            true
        } catch (e: Exception) {
            Log.e(TAG, "Error sending message", e)
            false
        }
    }

    suspend fun sendVoiceMessage(audioFilePath: String, conversationId: String): Boolean {
        return withContext(Dispatchers.IO) {
            try {
                val baseUrl = backendUrlRepository.currentUrl.value
                
                val file = java.io.File(audioFilePath)
                if (!file.exists()) {
                    Log.e(TAG, "Audio file not found: $audioFilePath")
                    return@withContext false
                }

                val requestBody = okhttp3.MultipartBody.Builder()
                    .setType(okhttp3.MultipartBody.FORM)
                    .addFormDataPart("cid", conversationId)
                    .addFormDataPart(
                        "file",
                        file.name,
                        okhttp3.RequestBody.create("audio/m4a".toMediaType(), file)
                    )
                    .build()

                val request = Request.Builder()
                    .url("$baseUrl/voice-message")
                    .post(requestBody)
                    .header("ngrok-skip-browser-warning", "true")
                    .build()

                val response = httpClient.newCall(request).execute()
                if (!response.isSuccessful) {
                    Log.e(TAG, "Voice message upload failed: ${response.code}")
                    return@withContext false
                }

                val responseBody = response.body?.string() ?: ""
                Log.d(TAG, "Voice message uploaded: $responseBody")
                response.close()
                true
            } catch (e: Exception) {
                Log.e(TAG, "Error uploading voice message", e)
                false
            }
        }
    }

    fun disconnect() {
        try {
            room?.disconnect()
        } catch (e: Exception) {
            Log.e(TAG, "Error disconnecting", e)
        }
        room = null
        localParticipant = null
        _connectionState.value = ChatConnectionState()
    }

    private suspend fun getChatToken(conversationId: String): Map<String, Any>? {
        return withContext(Dispatchers.IO) {
            try {
                val baseUrl = backendUrlRepository.currentUrl.value
                val body = """{"conversation_id":"$conversationId","participant_name":"mobile_user"}"""
                val requestBody = body.toRequestBody("application/json".toMediaType())

                val request = Request.Builder()
                    .url("$baseUrl/chat/token")
                    .post(requestBody)
                    .header("ngrok-skip-browser-warning", "true")
                    .build()

                val response = httpClient.newCall(request).execute()
                if (!response.isSuccessful) {
                    Log.e(TAG, "Token request failed: ${response.code}")
                    return@withContext null
                }

                val responseBody = response.body?.string() ?: return@withContext null
                val jsonResponse = json.parseToJsonElement(responseBody).jsonObject

                mapOf(
                    "token" to jsonResponse["token"]!!.jsonPrimitive.content,
                    "url" to jsonResponse["url"]!!.jsonPrimitive.content,
                    "room_name" to jsonResponse["room_name"]!!.jsonPrimitive.content
                )
            } catch (e: Exception) {
                Log.e(TAG, "Error getting chat token", e)
                null
            }
        }
    }

}
