package com.darius.crux.network

import retrofit2.Response
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.POST
import retrofit2.http.Path
import retrofit2.http.Query

interface CruxApi {

    @GET("dashboard/summary")
    suspend fun getDashboard(): Response<DashboardDTO>

    @GET("reports")
    suspend fun getReports(@Query("limit") limit: Int = 20): Response<List<ReportDTO>>

    @GET("reports/{id}")
    suspend fun getReport(@Path("id") id: Long): Response<ReportDTO>

    @POST("reports/generate")
    suspend fun generateReport(): Response<ReportDTO>

    @GET("integrations/status")
    suspend fun getIntegrationsStatus(): Response<IntegrationsStatusDTO>

    @GET("integrations/{provider}/authorize")
    suspend fun getAuthorizeUrl(@Path("provider") provider: String): Response<AuthorizeUrlDTO>

    @POST("integrations/{provider}/sync")
    suspend fun triggerSync(@Path("provider") provider: String): Response<SyncResultDTO>

    @GET("chat/history")
    suspend fun getChatHistory(@Query("limit") limit: Int = 50): Response<List<ChatMessageDTO>>

    @POST("chat")
    suspend fun sendChatMessage(@Body body: ChatRequestDTO): Response<ChatReplyDTO>

    @POST("devices")
    suspend fun registerDevice(@Body body: DeviceRegisterDTO): Response<Unit>
}
