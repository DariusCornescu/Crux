"""Upcoming work-calendar events for the Dashboard AGENDA block."""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import CalendarEvent
from app.schemas import UpcomingEvent

router = APIRouter(prefix="/calendar", tags=["calendar"])


@router.get("/upcoming", response_model=list[UpcomingEvent])
def upcoming(limit: int = Query(2, ge=1, le=10), db: Session = Depends(get_db)):
    rows = db.scalars(
        select(CalendarEvent)
        .where(CalendarEvent.start >= datetime.now(timezone.utc))
        .order_by(CalendarEvent.start)
        .limit(limit)
    ).all()
    return [UpcomingEvent(start=r.start, end=r.end, subject=r.subject,
                          attendee_count=r.attendee_count, is_recurring=r.is_recurring)
            for r in rows]
