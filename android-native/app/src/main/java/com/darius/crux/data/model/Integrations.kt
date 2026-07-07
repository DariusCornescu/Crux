package com.darius.crux.data.model

data class IntegrationState(val connected: Boolean, val lastSyncedAt: String?)

data class IntegrationsStatus(val strava: IntegrationState, val spotify: IntegrationState)
