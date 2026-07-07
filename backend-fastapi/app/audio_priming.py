"""Pre-session audio priming analysis (overnight Phase 4).

Correlates what was playing in the hour before a session with how good the
session was. Pure functions over Activity + ListeningSession lists.
Depends on Spotify audio features; when valence/energy are NULL (restricted
endpoint), profiles simply carry None for those fields.
"""
from datetime import datetime, timedelta, timezone

from app.models import Activity, EffortMode, ListeningSession

PRIMING_WINDOW_MIN = 60


def _aware(dt: datetime) -> datetime:
    return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt


def _avg(values: list) -> float | None:
    values = [v for v in values if v is not None]
    return round(sum(values) / len(values), 3) if values else None


def priming_profile(activity: Activity, listening: list[ListeningSession]) -> dict | None:
    """Avg valence/energy/tempo of tracks played within PRIMING_WINDOW_MIN
    before start_time. None if no tracks in the window."""
    start = _aware(activity.start_time)
    window_start = start - timedelta(minutes=PRIMING_WINDOW_MIN)
    tracks = [t for t in listening if window_start <= _aware(t.played_at) < start]
    if not tracks:
        return None
    return {
        "n": len(tracks),
        "valence": _avg([t.valence for t in tracks]),
        "energy": _avg([t.energy for t in tracks]),
        "tempo": _avg([t.tempo for t in tracks]),
    }


def _quality_metric(activity: Activity) -> tuple[float, bool] | None:
    """(metric, higher_is_better) for ranking within a mode; None if unrankable."""
    if activity.mode == EffortMode.explosive:
        return (min(activity.splits), False) if activity.splits else None
    if activity.mode == EffortMode.aerobic:
        pace = activity.avg_pace_s_per_km
        return (pace, False) if pace else None
    vert = activity.elevation_gain_m
    return (vert, True) if vert else None


def _avg_profiles(profiles: list[dict]) -> dict | None:
    if not profiles:
        return None
    return {
        "n": sum(p["n"] for p in profiles),
        "valence": _avg([p["valence"] for p in profiles]),
        "energy": _avg([p["energy"] for p in profiles]),
        "tempo": _avg([p["tempo"] for p in profiles]),
    }


def best_session_audio(activities: list[Activity], listening: list[ListeningSession]) -> dict:
    """Compare priming profiles of top-quartile sessions vs the rest.

    'Best' per mode: explosive→lowest best split; aerobic→lowest avg pace;
    loaded→highest elevation gain. Sessions without a quality metric or without
    a priming profile don't contribute; n_best/n_rest count contributing sessions.
    """
    by_mode: dict[EffortMode, list[tuple[Activity, float, bool]]] = {}
    for a in activities:
        metric = _quality_metric(a)
        if metric is not None:
            by_mode.setdefault(a.mode, []).append((a, metric[0], metric[1]))

    best_profiles: list[dict] = []
    rest_profiles: list[dict] = []
    for entries in by_mode.values():
        higher_better = entries[0][2]
        ranked = sorted(entries, key=lambda e: e[1], reverse=higher_better)
        n_best = max(1, len(ranked) // 4)
        for i, (activity, _, _) in enumerate(ranked):
            profile = priming_profile(activity, listening)
            if profile is None:
                continue
            (best_profiles if i < n_best else rest_profiles).append(profile)

    return {
        "best": _avg_profiles(best_profiles),
        "rest": _avg_profiles(rest_profiles),
        "n_best": len(best_profiles),
        "n_rest": len(rest_profiles),
    }
