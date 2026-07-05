"""Read-only insight endpoints."""
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import audio_priming
from app.database import get_db
from app.models import Activity, ListeningSession

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

