from celery import Celery
from celery.schedules import crontab

from app.config import get_settings

settings = get_settings()

celery_app = Celery("crux", broker=settings.redis_url, backend=settings.redis_url)
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

celery_app.conf.beat_schedule["sync-calendar"] = {
    "task": "app.workers.tasks.sync_calendar",
    "schedule": crontab(minute=15),
}
celery_app.conf.beat_schedule["wellness-rollup"] = {
    "task": "app.workers.tasks.wellness_rollup",
    "schedule": crontab(hour=4, minute=30),
}
# Pre-generate the day's quote + reflection before the user wakes, so the app
# never blocks on a cold first-of-day LLM call (which used to blow the client's
# 30s timeout and silently drop the quote). Runs just after wellness-rollup.
celery_app.conf.beat_schedule["prewarm-philosophy"] = {
    "task": "app.workers.tasks.prewarm_philosophy",
    "schedule": crontab(hour=4, minute=45),
}
celery_app.conf.beat_schedule["sync-github"] = {
    "task": "app.workers.tasks.sync_github",
    "schedule": crontab(minute=25),  # hourly, offset from calendar's :15
}
celery_app.conf.beat_schedule["meeting-reminders"] = {
    "task": "app.workers.tasks.meeting_reminders",
    "schedule": crontab(minute="*/5"),  # push reminders before imminent meetings
}

celery_app.autodiscover_tasks(["app.workers"])
