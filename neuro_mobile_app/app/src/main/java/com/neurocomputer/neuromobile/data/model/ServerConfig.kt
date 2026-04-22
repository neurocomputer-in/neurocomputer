package com.neurocomputer.neuromobile.data.model

import com.neurocomputer.neuromobile.BuildConfig

data class ServerConfig(
    val baseUrl: String,
    val wsUrl: String
) {
    companion object {
        val DESKTOP_URL: String = BuildConfig.SERVER_URL
        const val TIMEOUT_MS = 3000L
    }
}
