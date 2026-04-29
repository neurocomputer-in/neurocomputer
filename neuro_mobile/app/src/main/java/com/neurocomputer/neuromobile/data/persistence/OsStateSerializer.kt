package com.neurocomputer.neuromobile.data.persistence

import com.neurocomputer.neuromobile.data.model.WindowState
import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable
import kotlinx.serialization.json.Json

@Serializable
data class PersistedOsState(
    val windows: List<WindowState>,
    val activeWindowId: String?,
)

@Serializable
data class PersistedIconsState(
    val mobileOrder: List<String>,  // AppId names
    @SerialName("mobileDock") val dockPins: List<String>,
)

val osJson = Json { ignoreUnknownKeys = true; encodeDefaults = true }

fun PersistedOsState.toJson(): String = osJson.encodeToString(PersistedOsState.serializer(), this)
fun String.toPersistedOsState(): PersistedOsState = osJson.decodeFromString(PersistedOsState.serializer(), this)

fun PersistedIconsState.toJson(): String = osJson.encodeToString(PersistedIconsState.serializer(), this)
fun String.toPersistedIconsState(): PersistedIconsState = osJson.decodeFromString(PersistedIconsState.serializer(), this)
