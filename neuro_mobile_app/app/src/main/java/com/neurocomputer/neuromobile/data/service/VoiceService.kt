package com.neurocomputer.neuromobile.data.service

import com.neurocomputer.neuromobile.data.repository.BackendUrlRepository
import com.neurocomputer.neuromobile.domain.model.VoiceToken
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class VoiceService @Inject constructor(
    private val backendUrlRepository: BackendUrlRepository
) {
    private val _connectionState = MutableStateFlow<VoiceConnectionState>(VoiceConnectionState.Disconnected)
    val connectionState: StateFlow<VoiceConnectionState> = _connectionState.asStateFlow()

    private val _transcripts = MutableStateFlow<List<VoiceTranscript>>(emptyList())
    val transcripts: StateFlow<List<VoiceTranscript>> = _transcripts.asStateFlow()

    suspend fun getVoiceToken(userId: String): Result<VoiceToken> {
        return try {
            val baseUrl = backendUrlRepository.currentUrl.value
            val requestBody = """{"user_id":"$userId"}"""
                .toRequestBody("application/json".toMediaType())
            val request = Request.Builder()
                .url("$baseUrl/voice/token")
                .post(requestBody)
                .build()

            okhttp3.OkHttpClient().newCall(request).execute().use { response ->
                if (!response.isSuccessful) {
                    return Result.failure(Exception("HTTP ${response.code}"))
                }
                val body = response.body?.string() ?: return Result.failure(Exception("Empty response"))
                val json = kotlinx.serialization.json.Json { ignoreUnknownKeys = true }
                val data = json.decodeFromString<Map<String, String>>(body)
                Result.success(VoiceToken(
                    url = data["url"] ?: throw Exception("Missing url"),
                    token = data["token"] ?: throw Exception("Missing token"),
                    roomName = data["room_name"] ?: throw Exception("Missing room_name")
                ))
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    suspend fun connect(token: VoiceToken) {
        _connectionState.value = VoiceConnectionState.Connecting
        // LiveKit integration will be added when network is available
        _connectionState.value = VoiceConnectionState.Connected(token.roomName)
    }

    fun disconnect() {
        _connectionState.value = VoiceConnectionState.Disconnected
        _transcripts.value = emptyList()
    }
}

sealed class VoiceConnectionState {
    data object Disconnected : VoiceConnectionState()
    data object Connecting : VoiceConnectionState()
    data class Connected(val roomName: String) : VoiceConnectionState()
    data class Error(val message: String) : VoiceConnectionState()
}

data class VoiceTranscript(
    val id: String,
    val text: String,
    val isUser: Boolean
)
