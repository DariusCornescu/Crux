"""Deterministic subjective<->objective cross-references (overnight Phase 2).

Pure functions — no DB access. The report pipeline feeds the results to the
LLM as structured input; the offline fallback reports the counts.
"""
from datetime import datetime, timezone

from app.models import Activity, EffortMode, VoiceLog

BIG_VERT_M = 800


def _day(dt: datetime):
    return dt.date()


def subjective_flags(activities: list[Activity], voice_logs: list[VoiceLog]) -> list[dict]:
    """Deterministic cross-references. Each flag: {code, message, evidence:{...}}."""
    flags: list[dict] = []

    big_vert = [a for a in activities
                if a.mode == EffortMode.loaded and (a.elevation_gain_m or 0) > BIG_VERT_M]

    for log in voice_logs:
        symptoms = (log.extracted or {}).get("symptoms", [])
        if "heavy_legs" not in symptoms:
            continue
        log_day = _day(log.created_at)
        for activity in big_vert:
            days_after = (log_day - _day(activity.start_time)).days
            if days_after in (0, 1):
                vert = int(activity.elevation_gain_m or 0)
                when = "the same day as" if days_after == 0 else "one day after"
                flags.append({
                    "code": "heavy_legs_after_big_vert",
                    "message": (
                        f"Reported heavy legs on {log_day.isoformat()}, {when} a loaded "
                        f"session with {vert} m of elevation gain "
                        f"({_day(activity.start_time).isoformat()})."
                    ),
                    "evidence": {
                        "voice_log_id": log.id,
                        "activity_id": activity.id,
                        "elevation_gain_m": vert,
                        "days_after": days_after,
                    },
                })
    return flags
