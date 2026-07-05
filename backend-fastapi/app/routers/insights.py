"""Read-only insight endpoints (overnight Phases 4–5)."""
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import audio_priming, pacing
from app.database import get_db
from app.models import Activity, ListeningSession
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
