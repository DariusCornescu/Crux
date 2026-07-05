from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import voice_extract
from app.database import get_db
from app.models import Activity, ActivityType, VoiceLog
from app.schemas import VoiceLogCreate, VoiceLogOut

router = APIRouter(prefix="/voice-logs", tags=["voice-logs"])


def _same_day_activity(db: Session, created_at: datetime) -> int | None:
    """Most recent Activity on the same UTC calendar day, if any."""
    day_start = datetime.combine(created_at.date(), datetime.min.time(), tzinfo=timezone.utc)
    day_end = day_start + timedelta(days=1)
    activity = db.scalars(
        select(Activity)
        .where(Activity.start_time >= day_start, Activity.start_time < day_end)
        .order_by(Activity.start_time.desc())
        .limit(1)
    ).first()
    return activity.id if activity else None


@router.post("", response_model=VoiceLogOut, status_code=201)
def create_voice_log(payload: VoiceLogCreate, db: Session = Depends(get_db)):
    created_at = payload.created_at or datetime.now(timezone.utc)
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)

    result = voice_extract.extract(payload.transcript, payload.lang)

    activity_id = payload.activity_id
    if activity_id is None:
        activity_id = _same_day_activity(db, created_at)

    log = VoiceLog(
        created_at=created_at,
        activity_id=activity_id,
        lang=payload.lang,
        transcript=payload.transcript,
        perceived_effort=result["perceived_effort"],
        session_type=ActivityType(result["session_type"]) if result["session_type"] else None,
        notes=result["notes"],
        extraction_method=result["method"],
        extracted=result,
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return log


@router.get("", response_model=list[VoiceLogOut])
def list_voice_logs(limit: int = 50, db: Session = Depends(get_db)):
    return db.scalars(
        select(VoiceLog).order_by(VoiceLog.created_at.desc(), VoiceLog.id.desc()).limit(limit)
    ).all()
