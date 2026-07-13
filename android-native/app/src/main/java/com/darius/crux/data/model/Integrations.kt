package com.darius.crux.data.model

data class IntegrationState(
    val connected: Boolean,
    val lastSyncedAt: String?,
    val athleteId: String? = null,
)

data class IntegrationsStatus(
    val strava: IntegrationState,
    val spotify: IntegrationState,
    val calendar: IntegrationState? = null,
    val github: IntegrationState? = null,
)
