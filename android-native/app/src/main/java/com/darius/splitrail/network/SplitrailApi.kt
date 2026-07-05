package com.darius.splitrail.network

import retrofit2.Response
import retrofit2.http.GET
import retrofit2.http.POST
import retrofit2.http.Path

interface SplitrailApi {

    @GET("dashboard/summary")
    suspend fun getDashboard(): Response<DashboardDTO>

    @GET("integrations/status")
    suspend fun getIntegrationsStatus(): Response<IntegrationsStatusDTO>

    @GET("integrations/{provider}/authorize")
    suspend fun getAuthorizeUrl(@Path("provider") provider: String): Response<AuthorizeUrlDTO>

    @POST("integrations/{provider}/sync")
    suspend fun triggerSync(@Path("provider") provider: String): Response<SyncResultDTO>
}
