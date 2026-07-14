"""Daily readiness from sleep + resting HR + training load (DailySummary).
Honest LOW DATA state until wearable data (Health Connect) is flowing."""
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import DailySummary


def _recent_summary(db: Session) -> DailySummary | None:
    today = date.today()
    return db.scalar(
        select(DailySummary)
        .where(DailySummary.day >= today - timedelta(days=2))
        .order_by(DailySummary.day.desc())
    )


def compute(db: Session) -> dict:
    s = _recent_summary(db)
    sleep_min = s.sleep_duration_min if s else None
    rhr = s.resting_hr if s else None
    load = s.training_load if s else None

    score = 60.0
    have_recovery = False
    if sleep_min is not None:
        have_recovery = True
        score += max(-20.0, min(15.0, (sleep_min / 60 - 7) * 10))
    if rhr is not None:
        have_recovery = True
        score += max(-15.0, min(15.0, 55 - rhr))
    if load is not None:
        score += max(-20.0, min(10.0, (40 - load) / 4))

    score = int(max(0, min(100, round(score))))
    low_data = not have_recovery
    if low_data:
        label = "LOW DATA"
    elif score >= 67:
        label = "READY"
    elif score >= 34:
        label = "EASY"
    else:
        label = "REST"

    return {"score": score, "label": label, "low_data": low_data,
            "sleep_min": sleep_min, "resting_hr": rhr, "training_load": load}
