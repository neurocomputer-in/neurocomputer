package com.neurocomputer.neuromobile.data.service

import com.neurocomputer.neuromobile.data.repository.BackendUrlRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import javax.inject.Inject
import javax.inject.Singleton

data class OpenClawState(
    val connected: Boolean = false,
    val lastResponse: String = ""
)

@Singleton
class OpenClawService @Inject constructor(
    private val backendUrlRepository: BackendUrlRepository
) {
    private val _state = MutableStateFlow(OpenClawState())
    val state: StateFlow<OpenClawState> = _state.asStateFlow()

    private val client = okhttp3.OkHttpClient.Builder()
        .connectTimeout(10, java.util.concurrent.TimeUnit.SECONDS)
        .readTimeout(30, java.util.concurrent.TimeUnit.SECONDS)
        .writeTimeout(10, java.util.concurrent.TimeUnit.SECONDS)
        .build()

    suspend fun connect(): Boolean {
        return try {
            val baseUrl = backendUrlRepository.currentUrl.value
            val request = Request.Builder()
                .url("$baseUrl/openclaw/connect")
                .post("{}".toRequestBody("application/json".toMediaType()))
                .header("ngrok-skip-browser-warning", "true")
                .build()

            client.newCall(request).execute().use { resp ->
                if (resp.isSuccessful) {
                    _state.value = _state.value.copy(connected = true)
                    true
                } else {
                    _state.value = _state.value.copy(connected = false)
                    false
                }
            }
        } catch (e: Exception) {
            _state.value = _state.value.copy(connected = false)
            false
        }
    }

    suspend fun disconnect() {
        try {
            val baseUrl = backendUrlRepository.currentUrl.value
            val request = Request.Builder()
                .url("$baseUrl/openclaw/disconnect")
                .post("{}".toRequestBody("application/json".toMediaType()))
                .header("ngrok-skip-browser-warning", "true")
                .build()
            client.newCall(request).execute().close()
        } catch (_: Exception) { }
        _state.value = _state.value.copy(connected = false)
    }

    suspend fun sendMessage(text: String): Boolean {
        return try {
            val baseUrl = backendUrlRepository.currentUrl.value
            val body = """{"text":"$text"}"""
            val request = Request.Builder()
                .url("$baseUrl/openclaw/send")
                .post(body.toRequestBody("application/json".toMediaType()))
                .header("ngrok-skip-browser-warning", "true")
                .build()

            client.newCall(request).execute().use { resp ->
                if (resp.isSuccessful) {
                    val bodyStr = resp.body?.string() ?: ""
                    _state.value = _state.value.copy(lastResponse = bodyStr)
                    true
                } else {
                    false
                }
            }
        } catch (e: Exception) {
            false
        }
    }
}
