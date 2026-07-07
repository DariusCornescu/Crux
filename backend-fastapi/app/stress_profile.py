"""Hour-of-day stress profile x work-schedule overlay (Phase C).

Pure functions over WellnessSample / CalendarEvent / DailySummary lists.
Everything here is deterministic and OBSERVATIONAL — correlations cited with
their numbers, no causal claims (the report prompt says the same).

Stress basis: vendor stress_score (0-100) when present, else an inverted
HRV z-score mapped to the same scale (50 - 10z) with basis="hrv_inverted".
"""
from datetime import datetime, timedelta, timezone
from statistics import mean, pstdev
from zoneinfo import ZoneInfo

WORKDAYS = {0, 1, 2, 3, 4}
PEAK_RATIO = 1.10          # peak hour >= 10% above personal mean
HEAVY_MEETING_MIN = 180    # a "heavy" meeting day
GROUP_MIN_DAYS = 2         # each comparison group needs this many days
STRESS_DELTA_RATIO = 1.10  # heavy days >= 10% more stressed
SLEEP_DROP_RATIO = 0.90    # sleep score 10% lower
SLEEP_DROP_MIN = 30        # or 30 min shorter
RHR_DELTA_BPM = 3
AFTER_HOURS_START = 19
EARLY_MEETING_HOUR = 9


def _aware(dt: datetime) -> datetime:
    return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt


def _stress_points(samples, tz) -> tuple[list[tuple[datetime, float]], str | None]:
    stress = [s for s in samples if s.kind == "stress_score"]
    if stress:
        return [(_aware(s.recorded_at).astimezone(tz), float(s.value)) for s in stress], "stress_score"
    hrv = [s for s in samples if s.kind == "hrv_ms"]
    if not hrv:
        return [], None
    values = [float(s.value) for s in hrv]
    center, spread = mean(values), pstdev(values) or 1.0
    return [(_aware(s.recorded_at).astimezone(tz), 50 - 10 * ((float(s.value) - center) / spread))
            for s in hrv], "hrv_inverted"


def hourly_profile(samples: list, tz_name: str = "UTC") -> dict:
    """Avg stress per hour-of-day, split workday/weekend. None where no data."""
    points, basis = _stress_points(samples, ZoneInfo(tz_name))
    buckets: dict[str, list[list[float]]] = {
        "workday": [[] for _ in range(24)], "weekend": [[] for _ in range(24)]}
    for local_dt, value in points:
        key = "workday" if local_dt.weekday() in WORKDAYS else "weekend"
        buckets[key][local_dt.hour].append(value)
    return {
        "basis": basis,
        "n_samples": len(points),
        "workday": [round(mean(b), 1) if b else None for b in buckets["workday"]],
        "weekend": [round(mean(b), 1) if b else None for b in buckets["weekend"]],
    }


def _event_local(e, tz):
    start = e["start"] if isinstance(e, dict) else e.start
    end = e["end"] if isinstance(e, dict) else e.end
    return _aware(start).astimezone(tz), _aware(end).astimezone(tz)


def schedule_overlay(events: list, samples: list, dailies: list,
                     tz_name: str = "UTC") -> list[dict]:
    """Deterministic schedule<->stress cross-references. Observational only."""
    tz = ZoneInfo(tz_name)
    findings: list[dict] = []
    points, basis = _stress_points(samples, tz)

    # --- per-day helpers ---
    stress_by_day: dict = {}
    for local_dt, value in points:
        if local_dt.weekday() in WORKDAYS:
            stress_by_day.setdefault(local_dt.date(), []).append(value)
    day_stress = {d: mean(vs) for d, vs in stress_by_day.items()}

    meeting_min_by_day: dict = {}
    first_meeting_hour: dict = {}
    late_meeting_days: set = set()
    for e in events:
        start, end = _event_local(e, tz)
        day = start.date()
        meeting_min_by_day[day] = meeting_min_by_day.get(day, 0) + int((end - start).total_seconds() // 60)
        first_meeting_hour[day] = min(first_meeting_hour.get(day, 24), start.hour)
        if end.hour >= AFTER_HOURS_START:
            late_meeting_days.add(day)

    # 1) stress_peak_hours (workdays)
    profile = hourly_profile(samples, tz_name)
    present = [(h, v) for h, v in enumerate(profile["workday"]) if v is not None]
    if len(present) >= 4:
        overall = mean(v for _, v in present)
        peaks = sorted(present, key=lambda hv: -hv[1])[:2]
        if peaks[0][1] >= overall * PEAK_RATIO:
            hours = [h for h, _ in peaks]
            findings.append({
                "code": "stress_peak_hours",
                "message": (f"Workday stress peaks at {hours[0]:02d}:00 "
                            f"({peaks[0][1]:.0f} vs personal mean {overall:.0f})."),
                "evidence": {"hours": hours, "values": [v for _, v in peaks],
                             "mean": round(overall, 1), "basis": basis},
            })

    # 2) meeting_load_correlation (workdays with stress data)
    heavy = [d for d in day_stress if meeting_min_by_day.get(d, 0) >= HEAVY_MEETING_MIN]
    light = [d for d in day_stress if meeting_min_by_day.get(d, 0) < HEAVY_MEETING_MIN]
    if len(heavy) >= GROUP_MIN_DAYS and len(light) >= GROUP_MIN_DAYS:
        heavy_avg = mean(day_stress[d] for d in heavy)
        light_avg = mean(day_stress[d] for d in light)
        if heavy_avg >= light_avg * STRESS_DELTA_RATIO:
            findings.append({
                "code": "meeting_load_correlation",
                "message": (f"Days with ≥{HEAVY_MEETING_MIN // 60}h of meetings average "
                            f"{heavy_avg:.0f} stress vs {light_avg:.0f} on lighter days "
                            f"({len(heavy)} vs {len(light)} days)."),
                "evidence": {"heavy_avg": round(heavy_avg, 1), "light_avg": round(light_avg, 1),
                             "heavy_days": len(heavy), "light_days": len(light)},
            })

    # 3) after_hours_meetings_sleep — late meeting on D affects the night credited to D+1
    sleep_by_day = {d.day: (d.sleep_score, d.sleep_duration_min) for d in dailies
                    if d.sleep_score is not None or d.sleep_duration_min is not None}
    after = [sleep_by_day[d + timedelta(days=1)] for d in late_meeting_days
             if d + timedelta(days=1) in sleep_by_day]
    other = [v for day, v in sleep_by_day.items()
             if day - timedelta(days=1) not in late_meeting_days]
    if len(after) >= GROUP_MIN_DAYS and len(other) >= GROUP_MIN_DAYS:
        def _score(group):
            scores = [s for s, _ in group if s is not None]
            minutes = [m for _, m in group if m is not None]
            return (mean(scores) if scores else None, mean(minutes) if minutes else None)
        after_score, after_min = _score(after)
        other_score, other_min = _score(other)
        fires = (after_score is not None and other_score is not None
                 and after_score <= other_score * SLEEP_DROP_RATIO) or \
                (after_min is not None and other_min is not None
                 and after_min <= other_min - SLEEP_DROP_MIN)
        if fires:
            findings.append({
                "code": "after_hours_meetings_sleep",
                "message": (f"Nights after meetings ending ≥{AFTER_HOURS_START}:00 score "
                            f"{after_score:.0f} sleep vs {other_score:.0f} otherwise."
                            if after_score is not None and other_score is not None else
                            "Sleep is measurably shorter after late-evening meetings."),
                "evidence": {"after_nights": len(after), "other_nights": len(other),
                             "after_score": after_score, "other_score": other_score},
            })

    # 4) morning_meeting_rhr — first meeting before 09:00 vs same-day resting HR
    rhr_by_day = {d.day: d.resting_hr for d in dailies if d.resting_hr is not None}
    early = [rhr_by_day[d] for d, h in first_meeting_hour.items()
             if h < EARLY_MEETING_HOUR and d in rhr_by_day]
    normal = [rhr for day, rhr in rhr_by_day.items()
              if first_meeting_hour.get(day, 24) >= EARLY_MEETING_HOUR]
    if len(early) >= GROUP_MIN_DAYS and len(normal) >= GROUP_MIN_DAYS:
        if mean(early) >= mean(normal) + RHR_DELTA_BPM:
            findings.append({
                "code": "morning_meeting_rhr",
                "message": (f"Resting HR averages {mean(early):.0f} bpm on days starting with "
                            f"a pre-{EARLY_MEETING_HOUR}:00 meeting vs {mean(normal):.0f} otherwise."),
                "evidence": {"early_days": len(early), "normal_days": len(normal),
                             "early_avg": round(mean(early), 1), "normal_avg": round(mean(normal), 1)},
            })

    return findings
