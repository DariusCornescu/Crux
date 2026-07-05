"""Read-only insight endpoints (overnight Phases 4–5)."""
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import audio_priming, calendar_sync, pacing, stress_profile
from app.database import get_db
from app.config import get_settings
from app.models import (Activity, CalendarEvent, DailySummary, ListeningSession,
                        WellnessSample)
from app.schemas import PacingEstimateIn

router = APIRouter(tags=["insights"])

AUDIO_PRIMING_WINDOW_DAYS = 90


@router.get("/insights/audio-priming")
def audio_priming_insight(db: Session = Depends(get_db)) -> dict:
    since = datetime.now(timezone.utc) - timedelta(days=AUDIO_PRIMING_WINDOW_DAYS)
    activities = db.scalars(select(Activity).where(Activity.start_time >= since)).all()
    listening = db.scalars(
        select(ListeningSession).where(ListeningSession.played_at >= since)
    ).all()
    return audio_priming.best_session_audio(activities, listening)


PACING_HISTORY_DAYS = 180


@router.post("/pacing/estimate")
def pacing_estimate(payload: PacingEstimateIn, db: Session = Depends(get_db)) -> dict:
    since = datetime.now(timezone.utc) - timedelta(days=PACING_HISTORY_DAYS)
    history = db.scalars(select(Activity).where(Activity.start_time >= since)).all()
    return pacing.estimate(payload.distance_m, payload.elevation_gain_m, history)


STRESS_WINDOW_DAYS = 30


@router.get("/insights/stress-profile")
def stress_profile_insight(db: Session = Depends(get_db)) -> dict:
    since = datetime.now(timezone.utc) - timedelta(days=STRESS_WINDOW_DAYS)
    samples = db.scalars(select(WellnessSample).where(
        WellnessSample.recorded_at >= since,
        WellnessSample.kind.in_(["stress_score", "hrv_ms"]))).all()
    events = db.scalars(select(CalendarEvent).where(CalendarEvent.start >= since)).all()
    dailies = db.scalars(select(DailySummary).where(
        DailySummary.day >= since.date())).all()
    tz = get_settings().home_timezone
    return {
        "window_days": STRESS_WINDOW_DAYS,
        "hourly": stress_profile.hourly_profile(samples, tz),
        "findings": stress_profile.schedule_overlay(events, samples, dailies, tz),
        "meeting_load": calendar_sync.meeting_load(events, tz),
    }
