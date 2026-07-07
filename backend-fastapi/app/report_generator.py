"""Weekly analysis reports (build-order step 5).

Pipeline: aggregate the week per effort mode -> structured summary ->
Claude API -> Report row. Without ANTHROPIC_API_KEY the pipeline still runs
and stores a deterministic fallback report, so the Android Reports screen
can be built and tested before the key lands. FCM push is step 7.
"""
import json
import logging
import re
from pathlib import Path
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import llm
from app import calendar_sync, correlations, interference, stress_profile
from app.config import get_settings
from app.models import (Activity, CalendarEvent, DailySummary, EffortMode, Report,
                        VoiceLog, WellnessSample)

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are the analysis engine of Splitrail, a personal training
analytics app for one athlete: a former national 60m champion (PB 6.91) rebuilding
an aerobic base and preparing for mountaineering. His training has three distinct
physiological modes and your report must treat them as such:

- explosive: sprint / anaerobic power (neural work)
- aerobic: sustained endurance (engine work)
- loaded: rucking/hiking under load (structural work)

Write a weekly report in Markdown with exactly these sections:
## Gate (explosive), ## Strip (aerobic), ## Alti (loaded), ## Recovery & Mood,
## Next Week. Be concrete and quantitative; reference the numbers given. Flag
interference effects between modes (e.g. heavy aerobic volume blunting sprint
speed) when the data suggests them. No pleasantries, no generic advice.
When subjective reports are present, cross-reference them against the objective
numbers and explain correlations concretely (cite the day and the metric).
For each interference flag provided, explain the mechanism using the REFERENCE,
not just a warning. Use the schedule/stress data (schedule_stress) when advising
session placement — cite hours and numbers, and keep claims observational.

End your reply with a fenced ```json block:
{"headline": str, "wins": [str], "flags": [str], "focus_next_week": [str]}
"""


def week_bounds(week_start: date | None = None) -> tuple[date, date]:
    """Default period: the last fully completed Monday-Sunday week."""
    if week_start is None:
        today = date.today()
        week_start = today - timedelta(days=today.weekday() + 7)
    return week_start, week_start + timedelta(days=6)


def build_week_summary(db: Session, week_start: date, week_end: date) -> dict:
    start_dt = datetime.combine(week_start, datetime.min.time(), tzinfo=timezone.utc)
    end_dt = datetime.combine(week_end + timedelta(days=1), datetime.min.time(), tzinfo=timezone.utc)

    activities = db.scalars(
        select(Activity).where(Activity.start_time >= start_dt, Activity.start_time < end_dt)
        .order_by(Activity.start_time)
    ).all()

    explosive: dict = {"sessions": 0, "best_split": None, "all_splits": []}
    aerobic: dict = {"sessions": 0, "km": 0.0, "long_run_km": 0.0, "avg_pace_s_per_km": None}
    loaded: dict = {"sessions": 0, "vert_m": 0.0, "load_kg": None}
    paces: list[float] = []

    for a in activities:
        if a.mode == EffortMode.explosive:
            explosive["sessions"] += 1
            if a.splits:
                explosive["all_splits"] += a.splits
                best = min(a.splits)
                if explosive["best_split"] is None or best < explosive["best_split"]:
                    explosive["best_split"] = best
        elif a.mode == EffortMode.aerobic:
            aerobic["sessions"] += 1
            km = (a.distance_m or 0) / 1000
            aerobic["km"] = round(aerobic["km"] + km, 1)
            aerobic["long_run_km"] = max(aerobic["long_run_km"], round(km, 1))
            if a.avg_pace_s_per_km:
                paces.append(a.avg_pace_s_per_km)
        else:
            loaded["sessions"] += 1
            loaded["vert_m"] += a.elevation_gain_m or 0
            if a.load_kg:
                loaded["load_kg"] = a.load_kg

    if paces:
        aerobic["avg_pace_s_per_km"] = round(sum(paces) / len(paces))

    voice_logs = db.scalars(
        select(VoiceLog).where(VoiceLog.created_at >= start_dt, VoiceLog.created_at < end_dt)
        .order_by(VoiceLog.created_at)
    ).all()
    mode_by_id = {a.id: a.mode.value for a in activities}
    subjective = []
    for log in voice_logs:
        linked_mode = mode_by_id.get(log.activity_id)
        if linked_mode is None and log.activity_id is not None:
            linked = db.get(Activity, log.activity_id)
            linked_mode = linked.mode.value if linked else None
        subjective.append({
            "day": log.created_at.date().isoformat(),
            "perceived_effort": log.perceived_effort,
            "notes": log.notes,
            "symptoms": (log.extracted or {}).get("symptoms", []),
            "linked_mode": linked_mode,
        })

    summaries = db.scalars(
        select(DailySummary).where(DailySummary.day >= week_start, DailySummary.day <= week_end)
    ).all()
    calendar_events = db.scalars(select(CalendarEvent).where(
        CalendarEvent.start >= start_dt, CalendarEvent.start < end_dt)).all()
    wellness = db.scalars(select(WellnessSample).where(
        WellnessSample.recorded_at >= start_dt, WellnessSample.recorded_at < end_dt,
        WellnessSample.kind.in_(["stress_score", "hrv_ms"]))).all()
    tz = get_settings().home_timezone
    week_load = calendar_sync.meeting_load(calendar_events, tz)
    sleeps = [s.sleep_duration_min for s in summaries if s.sleep_duration_min]
    moods = [s.mood_valence for s in summaries if s.mood_valence is not None]

    return {
        "period": {"start": week_start.isoformat(), "end": week_end.isoformat()},
        "explosive": explosive,
        "aerobic": aerobic,
        "loaded": loaded,
        "subjective": subjective,
        "subjective_flags": correlations.subjective_flags(activities, voice_logs),
        "interference_flags": interference.detect(activities),
        "schedule_stress": {
            "meeting_minutes": week_load["total_minutes"],
            "after_hours_meetings": week_load["after_hours_count"],
            "max_back_to_back": week_load["max_back_to_back"],
            "findings": [f["message"] for f in stress_profile.schedule_overlay(
                calendar_events, wellness, summaries, tz)],
        },
        "conditions": {
            "avg_sleep_min": round(sum(sleeps) / len(sleeps)) if sleeps else None,
            "avg_mood_valence": round(sum(moods) / len(moods), 2) if moods else None,
        },
        "activities": [
            {
                "day": a.start_time.date().isoformat(),
                "type": a.type.value,
                "mode": a.mode.value,
                "name": a.name,
                "duration_s": a.duration_s,
                "distance_m": a.distance_m,
                "elevation_gain_m": a.elevation_gain_m,
                "splits": a.splits,
                "rpe": a.perceived_effort,
            }
            for a in activities
        ],
    }


def _fallback_report(summary: dict) -> tuple[str, dict]:
    e, a, l = summary["explosive"], summary["aerobic"], summary["loaded"]
    body = "\n".join([
        f"# Week {summary['period']['start']} – {summary['period']['end']}",
        "",
        "_Deterministic summary (ANTHROPIC_API_KEY not configured)._",
        "",
        "## Gate (explosive)",
        f"{e['sessions']} session(s), best split {e['best_split'] or '—'}.",
        "",
        "## Strip (aerobic)",
        f"{a['sessions']} session(s), {a['km']} km total, long run {a['long_run_km']} km.",
        "",
        "## Alti (loaded)",
        f"{l['sessions']} carry/carries, {int(l['vert_m'])} m vert, load {l['load_kg'] or '—'} kg.",
        "",
        "## Recovery & Mood",
        f"Avg sleep {summary['conditions']['avg_sleep_min'] or '—'} min, "
        f"avg mood valence {summary['conditions']['avg_mood_valence'] or '—'}.",
        "",
        "## Subjective",
        f"{len(summary.get('subjective', []))} voice log(s), "
        f"{len(summary.get('subjective_flags', []))} subjective flag(s).",
        "",
        "## Schedule",
        f"{summary.get('schedule_stress', {}).get('meeting_minutes', 0)} min of meetings, "
        f"{len(summary.get('schedule_stress', {}).get('findings', []))} stress finding(s).",
    ])
    highlights = {
        "headline": f"{a['km']} km aerobic, {int(l['vert_m'])} m vert, "
                    f"best split {e['best_split'] or 'n/a'}",
        "wins": [], "flags": [], "focus_next_week": [],
    }
    return body, highlights


def _knowledge_text() -> str:
    path = Path(__file__).parent / "knowledge" / "concurrent_training.md"
    try:
        return path.read_text(encoding="utf-8")
    except OSError:  # missing knowledge file must never kill a report
        logger.warning("knowledge file missing: %s", path)
        return ""


def _claude_report(summary: dict) -> tuple[str, dict]:
    system = SYSTEM_PROMPT + "\n\nREFERENCE (concurrent training):\n" + _knowledge_text()
    text = llm.complete(
        system=system,
        messages=[{"role": "user", "content": json.dumps(summary)}],
        max_tokens=2000,
    )

    highlights: dict = {}
    match = re.search(r"```json\s*(\{.*?\})\s*```", text, re.DOTALL)
    if match:
        try:
            highlights = json.loads(match.group(1))
        except json.JSONDecodeError:
            logger.warning("report highlights block was not valid JSON")
        text = text[: match.start()].rstrip()
    return text, highlights


def generate_weekly_report(db: Session, week_start: date | None = None) -> Report:
    start, end = week_bounds(week_start)
    summary = build_week_summary(db, start, end)

    if llm.is_configured():
        body, highlights = _claude_report(summary)
    else:
        body, highlights = _fallback_report(summary)

    # One weekly report per period — regenerating replaces it.
    report = db.scalar(select(Report).where(
        Report.kind == "weekly", Report.period_start == start))
    if report is None:
        report = Report(kind="weekly", period_start=start, period_end=end, body_md="")
        db.add(report)
    report.period_end = end
    report.body_md = body
    report.highlights = highlights
    report.created_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(report)
    return report
