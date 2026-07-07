package com.darius.splitrail.data.model

data class Report(
    val id: Long,
    val kind: String,        // weekly | monthly
    val periodStart: String, // ISO date
    val periodEnd: String,
    val bodyMd: String,
    val headline: String?,
    val createdAt: String,
)
