package com.neurocomputer.neuromobile.data.service

import com.neurocomputer.neuromobile.data.repository.BackendUrlRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import javax.inject.Inject
import javax.inject.Singleton

data class WindSurfState(
    val connected: Boolean = false,
    val hasPendingCommand: Boolean = false,
    val hasPendingChanges: Boolean = false,
    val pendingCommand: String = "",
    val lastResponse: String = ""
)

@Singleton
class WindSurfService @Inject constructor(
    private val backendUrlRepository: BackendUrlRepository
) {
    private val _state = MutableStateFlow(WindSurfState())
    val state: StateFlow<WindSurfState> = _state.asStateFlow()

    private val client = okhttp3.OkHttpClient.Builder()
        .connectTimeout(10, java.util.concurrent.TimeUnit.SECONDS)
        .readTimeout(30, java.util.concurrent.TimeUnit.SECONDS)
        .writeTimeout(10, java.util.concurrent.TimeUnit.SECONDS)
        .build()

    suspend fun connect(): Boolean {
        return try {
            val baseUrl = backendUrlRepository.currentUrl.value
            val request = Request.Builder()
                .url("$baseUrl/windsurf/connect")
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
                .url("$baseUrl/windsurf/disconnect")
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
                .url("$baseUrl/windsurf/send")
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

    suspend fun runCommand(): Boolean {
        return try {
            val baseUrl = backendUrlRepository.currentUrl.value
            val request = Request.Builder()
                .url("$baseUrl/windsurf/run")
                .post("{}".toRequestBody("application/json".toMediaType()))
                .header("ngrok-skip-browser-warning", "true")
                .build()

            client.newCall(request).execute().use { resp -> resp.isSuccessful }
        } catch (e: Exception) {
            false
        }
    }

    suspend fun acceptChanges(): Boolean {
        return try {
            val baseUrl = backendUrlRepository.currentUrl.value
            val request = Request.Builder()
                .url("$baseUrl/windsurf/accept")
                .post("{}".toRequestBody("application/json".toMediaType()))
                .header("ngrok-skip-browser-warning", "true")
                .build()

            client.newCall(request).execute().use { resp -> resp.isSuccessful }
        } catch (e: Exception) {
            false
        }
    }

    suspend fun rejectChanges(): Boolean {
        return try {
            val baseUrl = backendUrlRepository.currentUrl.value
            val request = Request.Builder()
                .url("$baseUrl/windsurf/reject")
                .post("{}".toRequestBody("application/json".toMediaType()))
                .header("ngrok-skip-browser-warning", "true")
                .build()

            client.newCall(request).execute().use { resp -> resp.isSuccessful }
        } catch (e: Exception) {
            false
        }
    }
}
