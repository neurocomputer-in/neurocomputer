package com.neurocomputer.neuromobile.domain.model

data class Message(
    val id: String,
    val text: String,
    val isUser: Boolean,
    val timestamp: Long = System.currentTimeMillis(),
    val isVoice: Boolean = false,
    val audioUrl: String? = null,
    val transcription: String? = null
)

data class Conversation(
    val id: String,
    val messages: List<Message> = emptyList(),
    val createdAt: Long = System.currentTimeMillis()
)
