package com.neurocomputer.neuromobile.domain.model

data class ConversationSummary(
    val id: String,
    val title: String,
    val lastMessage: String,
    val updatedAt: String,
    val agentId: String?
)
