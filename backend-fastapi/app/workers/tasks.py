from app.workers.celery_app import celery_app


@celery_app.task
def sync_strava() -> str:
    """Build-order step 2: pull new activities via Strava API, upsert Activity rows."""
    return "todo"


@celery_app.task
def sync_spotify() -> str:
    """Build-order step 4: pull recently played + audio features, upsert ListeningSession."""
    return "todo"


@celery_app.task
def generate_weekly_report() -> str:
    """Build-order step 5: aggregate week -> LLM -> Report -> push (step 7)."""
    return "todo"
