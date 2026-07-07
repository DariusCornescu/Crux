"""Work-calendar ingestion via published ICS feed (Phase B).

Chosen over Microsoft Graph because the account is a company M365 tenant —
publishing a calendar is user-level; Graph app registrations may need admin
consent. Graph can slot in behind sync_* later without downstream changes.
"""
import hashlib
import logging
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import httpx
import icalendar
import recurring_ical_events
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import CalendarEvent, OAuthToken

logger = logging.getLogger(__name__)

PROVIDER = "calendar_ics"
WINDOW_PAST_DAYS = 30
WINDOW_FUTURE_DAYS = 30
BACK_TO_BACK_GAP_MIN = 5
AFTER_HOURS_START = 19  # local hour

# Dedup aid, not a secret — documented in the spec.
_SUBJECT_SALT = b"crux-calendar-v1:"


def _hash_subject(subject: str) -> str:
    return hashlib.sha256(_SUBJECT_SALT + subject.encode("utf-8")).hexdigest()


def _window() -> tuple[datetime, datetime]:
    now = datetime.now(timezone.utc)
    return now - timedelta(days=WINDOW_PAST_DAYS), now + timedelta(days=WINDOW_FUTURE_DAYS)


def parse_ics(text: str, window_start: datetime, window_end: datetime) -> list[dict]:
    """Expand recurrences and normalize events. All-day entries are skipped —
    they are not meetings."""
    calendar = icalendar.Calendar.from_ical(text)
    # recurring_ical_events stamps RECURRENCE-ID on every occurrence and strips
    # RRULE, so recurrence is detected by UID against the source calendar.
    recurring_uids = {str(c.get("UID")) for c in calendar.walk("VEVENT") if c.get("RRULE")}
    occurrences = recurring_ical_events.of(calendar).between(window_start, window_end)

    events: list[dict] = []
    for component in occurrences:
        start = component.get("DTSTART").dt
        if not isinstance(start, datetime):  # date -> all-day
            continue
        end = component.get("DTEND").dt if component.get("DTEND") else start
        attendees = component.get("ATTENDEE")
        if attendees is None:
            attendee_count = None
        elif isinstance(attendees, list):
            attendee_count = len(attendees)
        else:
            attendee_count = 1
        events.append({
            "start": start if start.tzinfo else start.replace(tzinfo=timezone.utc),
            "end": end if end.tzinfo else end.replace(tzinfo=timezone.utc),
            "busy_status": str(component.get("X-MICROSOFT-CDO-BUSYSTATUS", "busy")).lower(),
            "attendee_count": attendee_count,
            "is_recurring": str(component.get("UID")) in recurring_uids,
            "subject_hash": _hash_subject(str(component.get("SUMMARY", ""))),
        })
    events.sort(key=lambda e: e["start"])
    return events


def sync_ics(db: Session, url: str | None = None) -> int:
    """Fetch + upsert the published calendar. Returns events in window."""
    url = url or get_settings().calendar_ics_url
    if not url:
        raise RuntimeError("calendar is not configured (CALENDAR_ICS_URL)")

    resp = httpx.get(url, timeout=30, follow_redirects=True)
    resp.raise_for_status()
    window_start, window_end = _window()
    events = parse_ics(resp.text, window_start, window_end)

    for data in events:
        row = db.scalar(select(CalendarEvent).where(
            CalendarEvent.source == "ics",
            CalendarEvent.subject_hash == data["subject_hash"],
            CalendarEvent.start == data["start"],
        ))
        if row is None:
            row = CalendarEvent(source="ics", **data)
            db.add(row)
        else:
            for key, value in data.items():
                setattr(row, key, value)

    token = db.scalar(select(OAuthToken).where(OAuthToken.provider == PROVIDER))
    if token is None:
        token = OAuthToken(provider=PROVIDER, access_token="ics")  # connection registry row
        db.add(token)
    token.last_synced_at = datetime.now(timezone.utc)
    db.commit()
    logger.info("calendar sync: %d events in window", len(events))
    return len(events)


def meeting_load(events: list, tz_name: str | None = None) -> dict:
    """Aggregate meeting exposure. Accepts CalendarEvent rows or parse_ics dicts."""
    tz = ZoneInfo(tz_name or get_settings().home_timezone)

    def _get(e, key):
        return e[key] if isinstance(e, dict) else getattr(e, key)

    def _aware(dt: datetime) -> datetime:
        return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt

    spans = sorted(
        ((_aware(_get(e, "start")).astimezone(tz), _aware(_get(e, "end")).astimezone(tz))
         for e in events),
        key=lambda s: s[0],
    )

    per_hour = [0] * 24
    days: set = set()
    total_minutes = 0
    first_meeting_hours: dict = {}
    after_hours = 0
    for start, end in spans:
        total_minutes += int((end - start).total_seconds() // 60)
        days.add(start.date())
        first = first_meeting_hours.get(start.date())
        first_meeting_hours[start.date()] = min(first, start.hour) if first is not None else start.hour
        if end.hour >= AFTER_HOURS_START:
            after_hours += 1
        cursor = start
        while cursor < end:
            bucket_end = (cursor.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1))
            chunk_end = min(end, bucket_end)
            per_hour[cursor.hour] += int((chunk_end - cursor).total_seconds() // 60)
            cursor = chunk_end

    max_streak = streak = 0
    prev_end = None
    for start, end in spans:
        if prev_end is not None and (start - prev_end) <= timedelta(minutes=BACK_TO_BACK_GAP_MIN):
            streak += 1
        else:
            streak = 1
        max_streak = max(max_streak, streak)
        prev_end = end

    return {
        "total_minutes": total_minutes,
        "days_with_meetings": len(days),
        "per_hour_minutes": per_hour,
        "max_back_to_back": max_streak,
        "after_hours_count": after_hours,
        "first_meeting_hour_avg": round(sum(first_meeting_hours.values()) / len(first_meeting_hours), 1)
        if first_meeting_hours else None,
    }
