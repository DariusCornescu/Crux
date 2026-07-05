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
def generate_weekly_report() -> str:
    """Build-order step 5: aggregate week -> LLM -> Report -> push (step 7)."""
    return "todo"
