package com.darius.crux.data

import com.darius.crux.data.model.AltiBlock
import com.darius.crux.data.model.Conditions
import com.darius.crux.data.model.DashboardData
import com.darius.crux.data.model.EffortMode
import com.darius.crux.data.model.GateBlock
import com.darius.crux.data.model.RailEntry
import com.darius.crux.data.model.StripBlock

/** Sample payload for Compose previews only — live data comes from the API. */
val sampleDashboard = DashboardData(
    week = 27,
    isDemo = true,
    conditions = Conditions(sleepMin = 432, restingHr = 52, steps = 8241, moodValence = 0.64),
    moodTrend = listOf(0.52, 0.61, null, 0.58, 0.66, 0.70, 0.63, null, 0.55, 0.60, 0.68, 0.72, 0.64, 0.64),
    rail = listOf(
        RailEntry(0, EffortMode.EXPLOSIVE, 3600, bestSplit = 6.98),
        RailEntry(1, EffortMode.AEROBIC, 2690, distanceM = 8200.0),
        RailEntry(2, EffortMode.LOADED, 5400, vertM = 540.0),
        RailEntry(4, EffortMode.EXPLOSIVE, 3000, bestSplit = 7.11),
        RailEntry(5, EffortMode.AEROBIC, 4704, distanceM = 14000.0),
        RailEntry(6, EffortMode.LOADED, 7200, vertM = 410.0),
    ),
    gate = GateBlock(
        bestSplit = 6.98,
        sessionNote = "60m fly ×3 · rest 8' · RPE 8",
        splits = listOf(7.04, 6.98, 7.02),
    ),
    strip = StripBlock(
        weekKm = 26.2,
        longRunKm = 14.0,
        z2Pct = 74,
        paceTrend = listOf(334, 331, 328, 330, 326, 329, 336, 332, 330, 327, 331, 335, 338, 341),
    ),
    alti = AltiBlock(vertM = 950.0, goalM = 2000.0, loadKg = 18.0, carries = 2),
)
