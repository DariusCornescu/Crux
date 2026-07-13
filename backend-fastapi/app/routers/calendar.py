"""Work-calendar events: upcoming (Dashboard AGENDA) + full history (Meetings screen)."""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import CalendarEvent
from app.schemas import CalendarEventOut, UpcomingEvent

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


@router.get("/events", response_model=list[CalendarEventOut])
def events(
    frm: datetime | None = Query(None, alias="from"),
    to: datetime | None = Query(None),
    limit: int = Query(200, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """All meetings, newest-first — past + future, for the Meetings screen. The
    client pins upcoming (start >= now) at the top and lists the rest as history.
    Exposes busy_status, which /upcoming omits."""
    stmt = select(CalendarEvent)
    if frm is not None:
        stmt = stmt.where(CalendarEvent.start >= frm)
    if to is not None:
        stmt = stmt.where(CalendarEvent.start < to)
    rows = db.scalars(
        stmt.order_by(CalendarEvent.start.desc()).limit(limit).offset(offset)
    ).all()
    return [CalendarEventOut(start=r.start, end=r.end, subject=r.subject,
                             busy_status=r.busy_status, attendee_count=r.attendee_count,
                             is_recurring=r.is_recurring)
            for r in rows]
