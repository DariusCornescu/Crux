"""FCM push (build-order step 7) — best effort by design.

Requires FCM_SERVICE_ACCOUNT_JSON_PATH (Firebase service-account key file).
Unconfigured or failing push never breaks report generation.
"""
import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import DeviceToken, Report

logger = logging.getLogger(__name__)


def send_report_notification(db: Session, report: Report) -> int:
    """Notify all registered devices about a new report. Returns #sent."""
    path = get_settings().fcm_service_account_json_path
    if not path:
        logger.info("FCM not configured — skipping push")
        return 0

    tokens = db.scalars(select(DeviceToken)).all()
    if not tokens:
        return 0

    try:
        import firebase_admin
        from firebase_admin import credentials, messaging

        if not firebase_admin._apps:
            firebase_admin.initialize_app(credentials.Certificate(path))

        headline = (report.highlights or {}).get("headline") or \
            f"{report.period_start} – {report.period_end}"
        sent = 0
        for t in tokens:
            try:
                messaging.send(messaging.Message(
                    notification=messaging.Notification(
                        title="SPLITRAIL — WEEKLY REPORT", body=headline),
                    data={"report_id": str(report.id)},
                    token=t.token,
                ))
                sent += 1
            except Exception as e:  # dead token etc. — log and continue
                logger.warning("push to token %s… failed: %s", t.token[:12], e)
        return sent
    except Exception as e:
        logger.warning("FCM unavailable: %s", e)
        return 0
