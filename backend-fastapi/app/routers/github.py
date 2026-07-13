"""GitHub contribution heatmap — dense per-day counts + streak/total stats."""
from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import DailyContribution

router = APIRouter(prefix="/github", tags=["github"])


class DayContribution(BaseModel):
    day: date
    count: int


class GithubHeatmapOut(BaseModel):
    days: list[DayContribution]   # oldest -> newest, dense (zero-filled)
    total: int
    current_streak: int
    longest_streak: int
    source: str                   # graphql | events | none


@router.get("/heatmap", response_model=GithubHeatmapOut)
def heatmap(weeks: int = Query(53, ge=1, le=53), db: Session = Depends(get_db)):
    today = datetime.now(timezone.utc).date()
    start = today - timedelta(days=weeks * 7 - 1)
    rows = db.scalars(
        select(DailyContribution)
        .where(DailyContribution.day >= start)
        .order_by(DailyContribution.day)
    ).all()
    by_day = {r.day: r.count for r in rows}
    source = rows[0].source if rows else "none"

    days: list[DayContribution] = []
    d = start
    while d <= today:
        days.append(DayContribution(day=d, count=by_day.get(d, 0)))
        d += timedelta(days=1)

    total = sum(x.count for x in days)

    longest = run = 0
    for x in days:
        if x.count > 0:
            run += 1
            longest = max(longest, run)
        else:
            run = 0

    # Current streak: consecutive active days ending today. A still-empty today
    # does not break a streak that ran through yesterday.
    current = 0
    for i, x in enumerate(reversed(days)):
        if x.count > 0:
            current += 1
        elif i == 0 and x.day == today:
            continue
        else:
            break

    return GithubHeatmapOut(days=days, total=total, current_streak=current,
                            longest_streak=longest, source=source)
