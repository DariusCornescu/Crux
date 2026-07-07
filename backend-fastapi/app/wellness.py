"""Wearable wellness data (stress-schedule-wearable spec, Phase A).

Flat service module: sample-kind registry + the daily roll-up that fills
DailySummary so the conditions strip and weekly reports see real sleep/RHR.
"""
import logging
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import DailySummary, WellnessSample

logger = logging.getLogger(__name__)

ALLOWED_KINDS = {
    "stress_score",   # vendor stress 0-100
    "hrv_ms",         # heart-rate variability (rMSSD ms)
    "resting_hr",     # bpm
    "sleep_minutes",  # minutes per sleep session (naps sum up)
    "sleep_score",    # vendor sleep quality 0-100
    "body_battery",   # Garmin-style energy 0-100
    "spo2",           # %
}


def rollup_daily(db: Session, days: int = 14) -> int:
    """Aggregate samples into DailySummary. Returns #days touched.

    sleep_minutes: SUM per day (multiple sessions), sleep_score: AVG,
    resting_hr: AVG rounded. Mood columns stay owned by the Spotify path.
    """
    since = datetime.combine(date.today() - timedelta(days=days),
                             datetime.min.time(), tzinfo=timezone.utc)
    rows = db.execute(
        select(
            func.date(WellnessSample.recorded_at),
            WellnessSample.kind,
            func.sum(WellnessSample.value),
            func.avg(WellnessSample.value),
        )
        .where(WellnessSample.recorded_at >= since,
               WellnessSample.kind.in_(["sleep_minutes", "sleep_score", "resting_hr"]))
        .group_by(func.date(WellnessSample.recorded_at), WellnessSample.kind)
    ).all()

    by_day: dict[date, dict] = {}
    for day_value, kind, total, avg in rows:
        day = day_value if isinstance(day_value, date) else date.fromisoformat(str(day_value))
        by_day.setdefault(day, {})[kind] = (total, avg)

    for day, kinds in by_day.items():
        summary = db.scalar(select(DailySummary).where(DailySummary.day == day))
        if summary is None:
            summary = DailySummary(day=day)
            db.add(summary)
        if "sleep_minutes" in kinds:
            summary.sleep_duration_min = int(round(kinds["sleep_minutes"][0]))
        if "sleep_score" in kinds:
            summary.sleep_score = round(float(kinds["sleep_score"][1]), 1)
        if "resting_hr" in kinds:
            summary.resting_hr = int(round(float(kinds["resting_hr"][1])))
    db.commit()
    return len(by_day)
