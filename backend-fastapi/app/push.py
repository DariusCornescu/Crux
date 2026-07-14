"""FCM push (build-order step 7) — best effort by design.

Requires FCM_SERVICE_ACCOUNT_JSON_PATH (Firebase service-account key file).
Unconfigured or failing push never breaks the caller.
"""
import logging
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import CalendarEvent, DeviceToken, Report

logger = logging.getLogger(__name__)

REMINDER_LEAD_MINUTES = 15


def _push_to_tokens(path: str, tokens, title: str, body: str, data: dict) -> int:
    """Deliver one notification to every device token. Returns #sent."""
    try:
        import firebase_admin
        from firebase_admin import credentials, messaging

        if not firebase_admin._apps:
            firebase_admin.initialize_app(credentials.Certificate(path))

        sent = 0
        for t in tokens:
            try:
                messaging.send(messaging.Message(
                    notification=messaging.Notification(title=title, body=body),
                    data=data, token=t.token))
                sent += 1
            except Exception as e:  # dead token etc. — log and continue
                logger.warning("push to token %s… failed: %s", t.token[:12], e)
        return sent
    except Exception as e:
        logger.warning("FCM unavailable: %s", e)
        return 0


def send_report_notification(db: Session, report: Report) -> int:
    """Notify all registered devices about a new report. Returns #sent."""
    path = get_settings().fcm_service_account_json_path
    if not path:
        logger.info("FCM not configured — skipping push")
        return 0
    tokens = db.scalars(select(DeviceToken)).all()
    if not tokens:
        return 0
    headline = (report.highlights or {}).get("headline") or \
        f"{report.period_start} – {report.period_end}"
    return _push_to_tokens(path, tokens, "CRUX — WEEKLY REPORT", headline,
                           {"type": "report", "report_id": str(report.id)})


def send_meeting_reminders(db: Session, lead_minutes: int = REMINDER_LEAD_MINUTES) -> int:
    """Push a reminder for each meeting starting within the next `lead_minutes`
    that hasn't been reminded yet, then mark it reminded. Returns #sent."""
    path = get_settings().fcm_service_account_json_path
    if not path:
        return 0
    now = datetime.now(timezone.utc)
    events = db.scalars(
        select(CalendarEvent).where(
            CalendarEvent.start >= now,
            CalendarEvent.start <= now + timedelta(minutes=lead_minutes),
            CalendarEvent.reminded_at.is_(None),
        ).order_by(CalendarEvent.start)
    ).all()
    if not events:
        return 0
    tokens = db.scalars(select(DeviceToken)).all()
    tz = ZoneInfo(get_settings().home_timezone)

    total = 0
    for ev in events:
        local = ev.start.astimezone(tz).strftime("%H:%M")
        total += _push_to_tokens(path, tokens, "CRUX — MEETING SOON",
                                 f"{ev.subject or 'Busy'} at {local}",
                                 {"type": "meeting", "event_id": str(ev.id)})
        ev.reminded_at = now
    db.commit()
    return total
