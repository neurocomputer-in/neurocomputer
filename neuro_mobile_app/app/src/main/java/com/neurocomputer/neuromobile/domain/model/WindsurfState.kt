package com.neurocomputer.neuromobile.domain.model

data class WindsurfState(
    val connected: Boolean = false,
    val hasPendingCommand: Boolean = false,
    val hasPendingChanges: Boolean = false,
    val pendingCommand: String = "",
    val lastResponse: String = ""
)

data class OpenClawState(
    val connected: Boolean = false,
    val lastResponse: String = "",
    val lastError: String = ""
)
