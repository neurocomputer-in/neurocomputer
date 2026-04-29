package com.neurocomputer.neuromobile.data.model

import kotlinx.serialization.Serializable

@Serializable
data class WindowState(
    val id: String,
    val zIndex: Int,
    val minimized: Boolean,
    val tabs: List<WindowTab>,
    val activeTabId: String,
)
