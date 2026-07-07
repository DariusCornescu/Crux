package com.darius.splitrail.data.model

data class ChatMessage(
    val id: Long,
    val role: String,      // user | assistant
    val content: String,
    val createdAt: String, // display string
)
