"""ICS published-calendar sync + meeting-load aggregation.

Fixture calendar: Mon 09:00 + Mon 10:00 back-to-back, a weekly RRULE (3
occurrences in window), one after-hours event, one all-day event (skipped).
All times UTC; meeting_load unit tests pass tz="UTC" explicitly.
"""
from datetime import datetime, timezone

import pytest

from app import calendar_sync
from app.config import get_settings
from app.models import CalendarEvent
from tests.conftest import FakeResponse

ICS = """BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Test//EN
BEGIN:VEVENT
UID:one@test
DTSTART:20260622T090000Z
DTEND:20260622T100000Z
SUMMARY:Sprint planning
ATTENDEE:mailto:a@x.com
ATTENDEE:mailto:b@x.com
END:VEVENT
BEGIN:VEVENT
UID:two@test
DTSTART:20260622T100000Z
DTEND:20260622T110000Z
SUMMARY:Design review
END:VEVENT
BEGIN:VEVENT
UID:weekly@test
DTSTART:20260623T140000Z
DTEND:20260623T153000Z
RRULE:FREQ=WEEKLY;COUNT=3
SUMMARY:Team sync
END:VEVENT
BEGIN:VEVENT
UID:late@test
DTSTART:20260624T183000Z
DTEND:20260624T193000Z
SUMMARY:Late review
END:VEVENT
BEGIN:VEVENT
UID:allday@test
DTSTART;VALUE=DATE:20260625
DTEND;VALUE=DATE:20260626
SUMMARY:Company holiday
END:VEVENT
END:VCALENDAR
"""

WINDOW_START = datetime(2026, 6, 21, tzinfo=timezone.utc)
WINDOW_END = datetime(2026, 7, 12, tzinfo=timezone.utc)


@pytest.fixture
def configured(monkeypatch):
    monkeypatch.setenv("CALENDAR_ICS_URL", "https://example.test/cal.ics")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_parse_expands_rrule_and_skips_all_day():
    events = calendar_sync.parse_ics(ICS, WINDOW_START, WINDOW_END)
    assert len(events) == 6  # 2 singles + 3 weekly occurrences + late; all-day skipped
    weekly = [e for e in events if e["is_recurring"]]
    assert len(weekly) == 3
    assert events[0]["attendee_count"] == 2


def test_sync_idempotent_and_no_raw_subjects(db, monkeypatch, configured):
    monkeypatch.setattr(calendar_sync.httpx, "get", lambda *a, **k: FakeResponse(text=ICS))
    monkeypatch.setattr(calendar_sync, "_window", lambda: (WINDOW_START, WINDOW_END))

    assert calendar_sync.sync_ics(db) == 6
    assert calendar_sync.sync_ics(db) == 6  # upsert, not duplicate
    rows = db.query(CalendarEvent).all()
    assert len(rows) == 6
    for row in rows:
        assert "Sprint" not in row.subject_hash and "Team" not in row.subject_hash
        assert len(row.subject_hash) == 64  # sha256 hex only


def test_sync_unconfigured_raises(db):
    get_settings.cache_clear()
    with pytest.raises(RuntimeError):
        calendar_sync.sync_ics(db)


def test_meeting_load_numbers():
    events = calendar_sync.parse_ics(ICS, WINDOW_START, WINDOW_END)
    load = calendar_sync.meeting_load(events, tz_name="UTC")
    # 60+60 + 3x90 + 60 = 450 minutes over 5 meeting days
    assert load["total_minutes"] == 450
    assert load["days_with_meetings"] == 5
    assert load["max_back_to_back"] == 2          # Mon 09-10 + 10-11
    assert load["after_hours_count"] == 1         # ends 19:30
    assert load["per_hour_minutes"][9] == 60      # Mon 09-10
    assert load["per_hour_minutes"][14] == 3 * 60  # weekly 14:00-15:30
    assert load["per_hour_minutes"][15] == 3 * 30


def test_endpoint_and_status(client, db, monkeypatch, configured):
    monkeypatch.setattr(calendar_sync.httpx, "get", lambda *a, **k: FakeResponse(text=ICS))
    monkeypatch.setattr(calendar_sync, "_window", lambda: (WINDOW_START, WINDOW_END))

    r = client.post("/integrations/calendar/sync")
    assert r.status_code == 200 and r.json()["synced"] == 6

    s = client.get("/integrations/status").json()
    assert s["calendar"]["connected"] is True
    assert s["calendar"]["last_synced_at"] is not None


def test_status_unconfigured(client):
    get_settings.cache_clear()
    assert client.get("/integrations/status").json()["calendar"]["connected"] is False
