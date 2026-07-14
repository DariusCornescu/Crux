"""Meeting-reminder push: selection window, dedupe via reminded_at, and the
FCM-unconfigured no-op. The actual FCM delivery (_push_to_tokens) is stubbed."""
from datetime import datetime, timedelta, timezone

import pytest

from app import push
from app.config import get_settings
from app.models import CalendarEvent, DeviceToken


@pytest.fixture
def fcm_configured(monkeypatch):
    monkeypatch.setenv("FCM_SERVICE_ACCOUNT_JSON_PATH", "/tmp/fake-sa.json")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def _event(now, minutes, subject, h):
    return CalendarEvent(start=now + timedelta(minutes=minutes),
                         end=now + timedelta(minutes=minutes + 30),
                         busy_status="busy", subject=subject, subject_hash=h, source="ics")


def test_meeting_reminders_unconfigured_noop(db):
    get_settings.cache_clear()
    assert push.send_meeting_reminders(db) == 0


def test_meeting_reminders_selects_window_marks_and_dedupes(db, monkeypatch, fcm_configured):
    calls = []
    monkeypatch.setattr(push, "_push_to_tokens",
                        lambda path, tokens, title, body, data: (calls.append(body) or len(list(tokens))))
    now = datetime.now(timezone.utc)
    db.add(DeviceToken(token="tok1"))
    db.add(_event(now, 8, "Standup", "h1"))         # within 15-min window
    db.add(_event(now, 360, "Later", "h2"))          # far future — excluded
    db.commit()

    assert push.send_meeting_reminders(db) == 1       # one token × one imminent event
    assert len(calls) == 1 and "Standup" in calls[0]
    assert push.send_meeting_reminders(db) == 0       # reminded_at set -> deduped


def test_meeting_reminders_skips_past_events(db, monkeypatch, fcm_configured):
    monkeypatch.setattr(push, "_push_to_tokens", lambda *a, **k: 1)
    now = datetime.now(timezone.utc)
    db.add(DeviceToken(token="tok1"))
    db.add(_event(now, -20, "Already started", "h3"))  # start < now — excluded
    db.commit()
    assert push.send_meeting_reminders(db) == 0
