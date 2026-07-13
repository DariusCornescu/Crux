from app.database import SessionLocal
from app.workers.celery_app import celery_app


@celery_app.task
def sync_strava() -> int:
    from app import strava

    db = SessionLocal()
    try:
        from sqlalchemy import select

        from app.models import OAuthToken
        if db.scalar(select(OAuthToken).where(OAuthToken.provider == "strava")) is None:
            return 0  # not connected yet — nothing to do
        return strava.sync_activities(db)
    finally:
        db.close()


@celery_app.task
def sync_spotify() -> int:
    from app import spotify

    db = SessionLocal()
    try:
        from sqlalchemy import select

        from app.models import OAuthToken
        if db.scalar(select(OAuthToken).where(OAuthToken.provider == "spotify")) is None:
            return 0
        return spotify.sync_recently_played(db)
    finally:
        db.close()


@celery_app.task
def generate_weekly_report() -> int:
    """Monday 05:00 UTC — report on the week that just ended. FCM push is step 7."""
    from app import report_generator

    from app import push

    db = SessionLocal()
    try:
        report = report_generator.generate_weekly_report(db)
        push.send_report_notification(db, report)  # best effort
        return report.id
    finally:
        db.close()


@celery_app.task
def wellness_rollup() -> int:
    """Daily safety net — ingest already triggers the roll-up inline."""
    from app import wellness

    db = SessionLocal()
    try:
        return wellness.rollup_daily(db)
    finally:
        db.close()


@celery_app.task
def sync_calendar() -> int:
    from app import calendar_sync
    from app.config import get_settings

    if not get_settings().calendar_ics_url:
        return 0
    db = SessionLocal()
    try:
        return calendar_sync.sync_ics(db)
    finally:
        db.close()


@celery_app.task
def sync_github() -> int:
    from app import github
    from app.config import get_settings

    if not get_settings().github_username:
        return 0  # not configured — nothing to do
    db = SessionLocal()
    try:
        return github.sync(db)
    finally:
        db.close()


@celery_app.task
def prewarm_philosophy() -> int:
    """Pre-generate today's mood, quote and reflection so the app never hits the
    cold first-of-day LLM path. Mood first — the reflection depends on it."""
    from app import mood, quotes, reflection

    db = SessionLocal()
    try:
        mood.get_current(db)
        quotes.get_today(db)
        reflection.get_today(db)
        return 1
    finally:
        db.close()
