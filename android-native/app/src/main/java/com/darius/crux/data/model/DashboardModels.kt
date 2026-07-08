package com.darius.crux.data.model

/** Domain models for the Dashboard — mapped from network DTOs in DTOs.kt. */

enum class EffortMode { EXPLOSIVE, AEROBIC, LOADED }

data class RailEntry(
    val dayIndex: Int,             // 0 = Monday
    val mode: EffortMode,
    val durationS: Int,
    val bestSplit: Double? = null, // explosive
    val distanceM: Double? = null, // aerobic
    val vertM: Double? = null,     // loaded
)

data class Conditions(val sleepMin: Int?, val restingHr: Int?, val moodValence: Double?)

data class GateBlock(
    val bestSplit: Double?,
    val sessionNote: String?,
    val splits: List<Double>,
)

data class StripBlock(
    val weekKm: Double,
    val longRunKm: Double,
    val z2Pct: Int?,
    val paceTrend: List<Int>, // s/km per km of most recent run
)

data class AltiBlock(
    val vertM: Double,
    val goalM: Double,
    val loadKg: Double?,
    val carries: Int,
)

data class DashboardData(
    val week: Int,
    val isDemo: Boolean = false,
    val conditions: Conditions,
    val moodTrend: List<Double?> = emptyList(), // 14 days, oldest first; null = no listening data
    val rail: List<RailEntry>,
    val gate: GateBlock,
    val strip: StripBlock,
    val alti: AltiBlock,
)
