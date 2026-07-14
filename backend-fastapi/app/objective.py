"""Training objective — a summit + date. Vertical banked accrues from logged
activities since start_date; days-to-go counts down to target_date."""
from datetime import date, datetime, time, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Activity, Objective


def get_active(db: Session) -> Objective | None:
    return db.scalar(
        select(Objective).where(Objective.active.is_(True)).order_by(Objective.created_at.desc())
    )


def banked_m(db: Session, obj: Objective) -> int:
    since = datetime.combine(obj.start_date, time.min, tzinfo=timezone.utc)
    total = db.scalar(
        select(func.coalesce(func.sum(Activity.elevation_gain_m), 0.0))
        .where(Activity.start_time >= since)
    )
    return int(total or 0)


def days_to_go(obj: Objective) -> int:
    return (obj.target_date - date.today()).days


def upsert(db: Session, name: str, target_date: date, vert_goal_m: int,
           elevation_m: int | None = None, start_date: date | None = None) -> Objective:
    """Create or update the single active objective."""
    obj = get_active(db)
    if obj is None:
        obj = Objective(name=name, target_date=target_date, vert_goal_m=vert_goal_m,
                        elevation_m=elevation_m, start_date=start_date or date.today())
        db.add(obj)
    else:
        obj.name = name
        obj.target_date = target_date
        obj.vert_goal_m = vert_goal_m
        obj.elevation_m = elevation_m
        if start_date is not None:
            obj.start_date = start_date
    db.commit()
    db.refresh(obj)
    return obj
