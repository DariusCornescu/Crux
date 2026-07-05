"""Mountaineering pacing heuristics (overnight Phase 5).

Deliberately simple and calibratable. Built and tested on SYNTHETIC fixtures —
the estimates need real-data calibration (a season of loaded sessions) before
they should be trusted on a mountain.

Duration model:
    time = elevation_gain_m / vert_speed_m_per_h * 3600
         + distance_m / flat_speed_m_s
where vert speed is the median sustained vertical speed from loaded history
(default 400 m/h without history) and flat speed derives from aerobic history
average pace (default 1.2 m/s). The two components are additive on purpose —
a conservative "Munter-style" first approximation.
"""
import statistics

from app.models import Activity, EffortMode

DEFAULT_VERT_SPEED_M_H = 400.0
DEFAULT_FLAT_SPEED_M_S = 1.2


def sustained_vertical_speed(loaded_activities: list[Activity]) -> float | None:
    """Median m of elevation gain per hour across loaded sessions with vert+duration."""
    rates = [
        (a.elevation_gain_m / a.duration_s) * 3600
        for a in loaded_activities
        if a.mode == EffortMode.loaded and (a.elevation_gain_m or 0) > 0 and (a.duration_s or 0) > 0
    ]
    return round(statistics.median(rates), 1) if rates else None


def estimate(distance_m: float, elevation_gain_m: float, history: list[Activity]) -> dict:
    """Personalized effort/pacing target for a planned ascent."""
    loaded = [a for a in history if a.mode == EffortMode.loaded]
    personal_vert = sustained_vertical_speed(loaded)
    vert_speed = personal_vert if personal_vert else DEFAULT_VERT_SPEED_M_H
    basis = "personal" if personal_vert else "default"

    paces = [a.avg_pace_s_per_km for a in history
             if a.mode == EffortMode.aerobic and a.avg_pace_s_per_km]
    flat_speed = (1000 / (sum(paces) / len(paces))) if paces else DEFAULT_FLAT_SPEED_M_S

    duration_s = elevation_gain_m / vert_speed * 3600 + distance_m / flat_speed

    notes = (
        f"Additive model: {int(elevation_gain_m)} m vert at {vert_speed:.0f} m/h "
        f"+ {distance_m / 1000:.1f} km at {flat_speed:.2f} m/s. "
        f"Basis '{basis}' — synthetic-fixture heuristic, needs real-data calibration "
        "before trusting on a mountain."
    )
    return {
        "est_duration_s": int(duration_s),
        "basis": basis,
        "vert_speed_m_per_h": round(vert_speed, 1),
        "notes": notes,
    }
