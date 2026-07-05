"""On-demand chat over the athlete's own data (build-order step 6).

Same shape as report_generator.py: assemble a compact data context ->
Claude API -> store both turns as ChatMessage rows. Without
ANTHROPIC_API_KEY it answers with a deterministic data snapshot, so the
Android chat UI is fully testable before the key lands.
"""
import json
import logging
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import audio_priming, llm, stress_profile
from app.config import get_settings
from app.models import (Activity, CalendarEvent, ChatMessage, DailySummary, EffortMode,
                        ListeningSession, Report, WellnessSample)

logger = logging.getLogger(__name__)

HISTORY_TURNS = 10  # prior messages handed to Claude

SYSTEM_PROMPT = """You are Splitrail's chat analyst — the on-demand counterpart of
its weekly reports. One athlete: former national 60m champion (PB 6.91),
rebuilding an aerobic base, preparing for mountaineering. Three physiological
modes, always treated distinctly: explosive (sprint/anaerobic), aerobic
(endurance), loaded (ruck/hike under load).

You receive a JSON snapshot of his recent data below. Answer questions about
it concretely and quantitatively; say plainly when the data can't answer the
question. Flag interference between modes when relevant. Keep replies short —
this is a phone chat, not a report. Markdown allowed, sparingly.

DATA SNAPSHOT:
"""


def build_context(db: Session, days: int = 28) -> dict:
    since = datetime.now(timezone.utc) - timedelta(days=days)
    activities = db.scalars(
        select(Activity).where(Activity.start_time >= since).order_by(Activity.start_time)
    ).all()

    per_mode = {m.value: {"sessions": 0} for m in EffortMode}
    km = vert = 0.0
    best_split = None
    for a in activities:
        per_mode[a.mode.value]["sessions"] += 1
        if a.mode == EffortMode.aerobic:
            km += (a.distance_m or 0) / 1000
        elif a.mode == EffortMode.loaded:
            vert += a.elevation_gain_m or 0
        elif a.splits:
            s = min(a.splits)
            best_split = s if best_split is None or s < best_split else best_split

    summaries = db.scalars(
        select(DailySummary).order_by(DailySummary.day.desc()).limit(14)
    ).all()
    latest_report = db.scalars(
        select(Report).order_by(Report.created_at.desc()).limit(1)
    ).first()
    listening = db.scalars(
        select(ListeningSession).where(ListeningSession.played_at >= since)
    ).all()
    wellness = db.scalars(select(WellnessSample).where(
        WellnessSample.recorded_at >= since,
        WellnessSample.kind.in_(["stress_score", "hrv_ms"]))).all()
    calendar_events = db.scalars(select(CalendarEvent).where(CalendarEvent.start >= since)).all()

    return {
        "window_days": days,
        "totals": {"aerobic_km": round(km, 1), "loaded_vert_m": int(vert),
                   "best_split_s": best_split,
                   "sessions_per_mode": {k: v["sessions"] for k, v in per_mode.items()}},
        "recent_daily": [
            {"day": s.day.isoformat(), "sleep_min": s.sleep_duration_min,
             "mood_valence": s.mood_valence, "resting_hr": s.resting_hr}
            for s in summaries
        ],
        "latest_report_highlights": latest_report.highlights if latest_report else None,
        "audio_priming": audio_priming.best_session_audio(activities, listening),
        "stress_profile": {
            "findings": [f["message"] for f in stress_profile.schedule_overlay(
                calendar_events, wellness, summaries,
                get_settings().home_timezone)],
            "hourly_workday": stress_profile.hourly_profile(
                wellness, get_settings().home_timezone)["workday"],
        },
        "activities": [
            {"day": a.start_time.date().isoformat(), "type": a.type.value,
             "mode": a.mode.value, "name": a.name, "duration_s": a.duration_s,
             "distance_m": a.distance_m, "elevation_gain_m": a.elevation_gain_m,
             "splits": a.splits, "rpe": a.perceived_effort}
            for a in activities
        ],
    }


def _fallback_reply(context: dict) -> str:
    t = context["totals"]
    return (
        "CHAT OFFLINE MODE — ANTHROPIC_API_KEY not configured. "
        f"Snapshot of the last {context['window_days']} days: "
        f"{t['aerobic_km']} km aerobic, {t['loaded_vert_m']} m vert under load, "
        f"best split {t['best_split_s'] or 'n/a'}, "
        f"sessions {t['sessions_per_mode']}."
    )


def _claude_reply(context: dict, history: list[ChatMessage], message: str) -> str:
    messages = [
        {"role": "user" if m.role == "user" else "assistant", "content": m.content}
        for m in history
    ]
    messages.append({"role": "user", "content": message})
    return llm.complete(
        system=SYSTEM_PROMPT + json.dumps(context),
        messages=messages,
        max_tokens=1000,
    )


def send_message(db: Session, message: str) -> str:
    history = list(reversed(db.scalars(
        select(ChatMessage).order_by(ChatMessage.created_at.desc()).limit(HISTORY_TURNS)
    ).all()))

    db.add(ChatMessage(role="user", content=message))
    context = build_context(db)

    if llm.is_configured():
        try:
            reply = _claude_reply(context, history, message)
        except Exception as e:  # store the failure as the reply — visible in the UI
            logger.error("Claude chat call failed: %s", e)
            reply = f"SIGNAL LOST — Claude call failed ({e})."
    else:
        reply = _fallback_reply(context)

    db.add(ChatMessage(role="assistant", content=reply))
    db.commit()
    return reply
