"""Training contribution grid — per-day dominant mode + volume from activities,
the training counterpart of the GitHub code grid."""
from datetime import date, datetime, time, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Activity


def grid(db: Session, weeks: int) -> dict:
    today = date.today()
    start = today - timedelta(days=weeks * 7 - 1)
    since = datetime.combine(start, time.min, tzinfo=timezone.utc)
    rows = db.scalars(
        select(Activity).where(Activity.start_time >= since).order_by(Activity.start_time)
    ).all()

    by_day: dict[date, dict[str, float]] = {}
    for a in rows:
        d = a.start_time.date()
        if d < start:
            continue
        mode = a.mode.value  # explosive | aerobic | loaded
        m = by_day.setdefault(d, {})
        m[mode] = m.get(mode, 0.0) + (a.duration_s or 0) / 60.0

    days = []
    active_days = 0
    d = start
    while d <= today:
        modes = by_day.get(d)
        if modes:
            active_days += 1
            dominant = max(modes, key=modes.get)
            minutes = int(sum(modes.values()))
        else:
            dominant, minutes = None, 0
        days.append({"day": d, "mode": dominant, "minutes": minutes})
        d += timedelta(days=1)

    total_km = sum((a.distance_m or 0) for a in rows) / 1000.0
    return {"days": days, "total_sessions": len(rows), "active_days": active_days,
            "total_km": round(total_km, 1)}
