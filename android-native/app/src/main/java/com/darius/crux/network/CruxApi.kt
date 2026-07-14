package com.darius.crux.network

import retrofit2.Response
import retrofit2.http.Body
import retrofit2.http.DELETE
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

    @GET("reports/{id}/metrics")
    suspend fun getReportMetrics(@Path("id") id: Int): Response<ReportMetricsDTO>

    @GET("integrations/status")
    suspend fun getIntegrationsStatus(): Response<IntegrationsStatusDTO>

    @GET("integrations/{provider}/authorize")
    suspend fun getAuthorizeUrl(@Path("provider") provider: String): Response<AuthorizeUrlDTO>

    @POST("integrations/{provider}/sync")
    suspend fun triggerSync(@Path("provider") provider: String): Response<SyncResultDTO>

    @POST("integrations/push/test")
    suspend fun pushTest(): Response<SyncResultDTO>

    @GET("chat/history")
    suspend fun getChatHistory(@Query("limit") limit: Int = 50): Response<List<ChatMessageDTO>>

    @POST("chat")
    suspend fun sendChatMessage(@Body body: ChatRequestDTO): Response<ChatReplyDTO>

    @DELETE("chat/history")
    suspend fun clearChatHistory(): Response<Unit>

    @POST("devices")
    suspend fun registerDevice(@Body body: DeviceRegisterDTO): Response<Unit>

    @GET("calendar/upcoming")
    suspend fun getUpcomingEvents(@Query("limit") limit: Int = 2): Response<List<UpcomingEventDTO>>

    @GET("calendar/events")
    suspend fun getCalendarEvents(
        @Query("from") from: String? = null,
        @Query("limit") limit: Int = 200,
    ): Response<List<CalendarEventDTO>>

    @GET("quote/today")
    suspend fun getQuoteToday(): Response<QuoteDTO>

    @GET("quote/archive")
    suspend fun getQuoteArchive(@Query("limit") limit: Int = 30): Response<List<QuoteDTO>>

    @GET("reflection/today")
    suspend fun getReflectionToday(): Response<ReflectionDTO>

    @GET("mood/current")
    suspend fun getMoodCurrent(): Response<MoodDTO>

    @GET("signals/detail")
    suspend fun getSignalsDetail(): Response<SignalsDTO>

    @GET("github/heatmap")
    suspend fun getGithubHeatmap(@Query("weeks") weeks: Int = 53): Response<GithubHeatmapDTO>
}
