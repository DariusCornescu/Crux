"""Concurrent-training interference rules (overnight Phase 3).

Deterministic session-sequencing checks. Pure functions — the report pipeline
feeds the flags plus app/knowledge/concurrent_training.md to the LLM so it can
explain WHY a flag matters, not just emit a warning.
"""
from datetime import datetime, timedelta, timezone

from app.models import Activity, EffortMode

WINDOW = timedelta(hours=48)
LONG_AEROBIC_M = 12000
BIG_VERT_M = 800


def _aware(dt: datetime) -> datetime:
    return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt


def detect(activities: list[Activity]) -> list[dict]:
    """Session-sequencing interference flags.

    Each flag: {code, message, activity_ids: [earlier_id, later_id], pattern_ref}.
    """
    flags: list[dict] = []
    ordered = sorted(activities, key=lambda a: _aware(a.start_time))

    for i, earlier in enumerate(ordered):
        for later in ordered[i + 1:]:
            gap = _aware(later.start_time) - _aware(earlier.start_time)
            if gap <= timedelta(0):
                continue
            if gap > WINDOW:
                break  # ordered by time — everything further is out of window too
            hours = round(gap.total_seconds() / 3600)

            if (earlier.mode == EffortMode.aerobic
                    and (earlier.distance_m or 0) >= LONG_AEROBIC_M
                    and later.mode == EffortMode.explosive):
                flags.append({
                    "code": "aerobic_blunts_sprint",
                    "message": (
                        f"Sprint session {hours}h after a "
                        f"{(earlier.distance_m or 0) / 1000:.1f} km aerobic session — "
                        "neural quality likely blunted."
                    ),
                    "activity_ids": [earlier.id, later.id],
                    "pattern_ref": "concurrent-training#aerobic-before-speed",
                })

            if (earlier.mode == EffortMode.explosive
                    and later.mode == EffortMode.aerobic
                    and (later.distance_m or 0) >= LONG_AEROBIC_M):
                flags.append({
                    "code": "sprint_before_recovery",
                    "message": (
                        f"{(later.distance_m or 0) / 1000:.1f} km aerobic session {hours}h "
                        "after a sprint session — compromised sprint adaptation / "
                        "insufficient recovery."
                    ),
                    "activity_ids": [earlier.id, later.id],
                    "pattern_ref": "concurrent-training#recovery-windows",
                })

            if (earlier.mode == EffortMode.loaded
                    and (earlier.elevation_gain_m or 0) > BIG_VERT_M
                    and later.mode == EffortMode.explosive):
                flags.append({
                    "code": "loaded_before_sprint",
                    "message": (
                        f"Sprint session {hours}h after a loaded session with "
                        f"{int(earlier.elevation_gain_m or 0)} m vert — structural "
                        "fatigue carried into neural work."
                    ),
                    "activity_ids": [earlier.id, later.id],
                    "pattern_ref": "concurrent-training#structural-fatigue",
                })
    return flags
