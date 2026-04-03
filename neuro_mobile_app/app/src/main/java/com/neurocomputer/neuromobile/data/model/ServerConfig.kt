package com.neurocomputer.neuromobile.data.model

// Local config - DO NOT COMMIT
// This file is gitignored

data class ServerConfig(
    val baseUrl: String,
    val wsUrl: String
) {
    companion object {
        const val DESKTOP_URL = "https://desktop-0001.neurocomputer.in"
        const val TIMEOUT_MS = 3000L
    }
}
