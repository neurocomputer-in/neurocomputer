package com.neurocomputer.neuromobile.data.repository

import android.content.Context
import androidx.datastore.core.DataStore
import androidx.datastore.preferences.core.Preferences
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.stringPreferencesKey
import androidx.datastore.preferences.preferencesDataStore
import com.neurocomputer.neuromobile.data.model.ServerConfig
import dagger.hilt.android.qualifiers.ApplicationContext
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.withContext
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.flow.map
import okhttp3.OkHttpClient
import okhttp3.Request
import java.net.InetAddress
import java.util.concurrent.TimeUnit
import javax.inject.Inject
import javax.inject.Singleton

private val Context.dataStore: DataStore<Preferences> by preferencesDataStore(name = "neuro_settings")

sealed class BackendHealthState {
    data object Unknown : BackendHealthState()
    data object Checking : BackendHealthState()
    data object Healthy : BackendHealthState()
    data class Unhealthy(val reason: String) : BackendHealthState()
}

@Singleton
class BackendUrlRepository @Inject constructor(
    @ApplicationContext private val context: Context
) {
    private val okHttpClient = OkHttpClient.Builder()
        .connectTimeout(3, TimeUnit.SECONDS)
        .readTimeout(3, TimeUnit.SECONDS)
        .build()

    private val _currentUrl = MutableStateFlow(ServerConfig.DESKTOP_URL)
    val currentUrl: StateFlow<String> = _currentUrl.asStateFlow()

    private val _wsUrl = MutableStateFlow(
        ServerConfig.DESKTOP_URL.replace("http://", "ws://").replace("https://", "wss://") + "/ws"
    )
    val wsUrl: StateFlow<String> = _wsUrl.asStateFlow()

    private val _healthState = MutableStateFlow<BackendHealthState>(BackendHealthState.Unknown)
    val healthState: StateFlow<BackendHealthState> = _healthState.asStateFlow()

    // Selected agent - synced between app and overlay
    private val _selectedAgent = MutableStateFlow("neuro")
    val selectedAgent: StateFlow<String> = _selectedAgent.asStateFlow()

    suspend fun init() {
        // Load saved agent first
        loadSelectedAgent()
        
        // Check for manually saved URL first
        val savedUrl = context.dataStore.data.map { prefs ->
            prefs[SAVED_URL_KEY]
        }.first()

        if (!savedUrl.isNullOrBlank()) {
            // Re-probe saved URL - if it's stale/invalid, discard it
            if (probeUrl(savedUrl)) {
                setUrl(savedUrl)
                return
            }
            // Saved URL no longer valid — clear it
            context.dataStore.edit { prefs ->
                prefs.remove(SAVED_URL_KEY)
            }
        }

        // Use default desktop URL
        setUrl(ServerConfig.DESKTOP_URL)
    }

    private suspend fun loadSelectedAgent() {
        val savedAgent = context.dataStore.data.map { prefs ->
            prefs[SELECTED_AGENT_KEY]
        }.first()
        if (!savedAgent.isNullOrBlank()) {
            _selectedAgent.value = savedAgent
        }
    }

    suspend fun setSelectedAgent(agentId: String) {
        _selectedAgent.value = agentId
        context.dataStore.edit { prefs ->
            prefs[SELECTED_AGENT_KEY] = agentId
        }
    }

    private fun probeUrl(url: String): Boolean {
        return try {
            val request = Request.Builder()
                .url("$url/health")
                .get()
                .build()
            val response = okHttpClient.newCall(request).execute()
            response.isSuccessful
        } catch (e: Exception) {
            false
        }
    }

    suspend fun checkHealth() {
        _healthState.value = BackendHealthState.Checking
        try {
            val result = withContext(Dispatchers.IO) {
                val request = Request.Builder()
                    .url("${_currentUrl.value}/health")
                    .get()
                    .build()
                okHttpClient.newCall(request).execute().use { response ->
                    if (response.isSuccessful) "healthy" else "unhealthy:${response.code}"
                }
            }
            _healthState.value = if (result == "healthy") BackendHealthState.Healthy
                else BackendHealthState.Unhealthy("HTTP ${result.removePrefix("unhealthy:")}")
        } catch (e: Exception) {
            val reason = when {
                e.javaClass.name.contains("UnknownHost", ignoreCase = true) -> "DNS error: ${e.message ?: "unknown host"}"
                e.javaClass.name.contains("Timeout", ignoreCase = true) -> "Timeout: ${e.message ?: "connection timed out"}"
                e.javaClass.name.contains("Certificate", ignoreCase = true) -> "SSL error: ${e.message ?: "certificate problem"}"
                e.javaClass.name.contains("Socket", ignoreCase = true) -> "Socket error: ${e.message ?: "connection failed"}"
                e.message.isNullOrBlank() -> "Network error (${e.javaClass.simpleName})"
                else -> "${e.message}"
            }
            _healthState.value = BackendHealthState.Unhealthy(reason)
        }
    }

    suspend fun setUrl(url: String): String {
        val normalized = normalizeUrl(url)
        _currentUrl.value = normalized
        _wsUrl.value = normalized
            .replace("http://", "ws://")
            .replace("https://", "wss://") + "/ws"

        context.dataStore.edit { prefs ->
            prefs[SAVED_URL_KEY] = normalized
        }
        checkHealth()
        return normalized
    }

    private fun normalizeUrl(url: String): String {
        var u = url.trim().trimEnd('/')
        if (!u.startsWith("http://") && !u.startsWith("https://")) {
            u = "https://$u"
        }
        return u
    }

    companion object {
        private val SAVED_URL_KEY = stringPreferencesKey("saved_backend_url")
        private val SELECTED_AGENT_KEY = stringPreferencesKey("selected_agent")
    }
}
