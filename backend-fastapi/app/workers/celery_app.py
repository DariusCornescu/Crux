from celery import Celery
from celery.schedules import crontab

from app.config import get_settings

settings = get_settings()

celery_app = Celery("splitrail", broker=settings.redis_url, backend=settings.redis_url)
celery_app.conf.timezone = "UTC"
celery_app.conf.beat_schedule = {
    "weekly-report": {
        "task": "app.workers.tasks.generate_weekly_report",
        "schedule": crontab(day_of_week="mon", hour=5, minute=0),
    },
    "sync-strava": {
        "task": "app.workers.tasks.sync_strava",
        "schedule": crontab(minute="*/30"),
    },
    "sync-spotify": {
        "task": "app.workers.tasks.sync_spotify",
        "schedule": crontab(minute="*/45"),
    },
}

celery_app.autodiscover_tasks(["app.workers"])
