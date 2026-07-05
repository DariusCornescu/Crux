from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Activity
from app.schemas import ActivityCreate, ActivityOut

router = APIRouter(prefix="/activities", tags=["activities"])


@router.get("", response_model=list[ActivityOut])
def list_activities(limit: int = 50, db: Session = Depends(get_db)):
    rows = db.scalars(select(Activity).order_by(Activity.start_time.desc()).limit(limit)).all()
    return rows


@router.post("", response_model=ActivityOut, status_code=201)
def create_activity(payload: ActivityCreate, db: Session = Depends(get_db)):
    """Manual entry — sprint sessions won't come from Strava with split fidelity."""
    activity = Activity(source="manual", **payload.model_dump())
    db.add(activity)
    db.commit()
    db.refresh(activity)
    return activity
