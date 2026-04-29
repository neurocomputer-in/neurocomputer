package com.neurocomputer.neuromobile.domain.model

data class Workspace(
    val id: String,
    val name: String,
    val description: String = "",
    val color: String = "#8B5CF6",
    val emoji: String = "🏢",
    val agents: List<String> = listOf("neuro"),
)
