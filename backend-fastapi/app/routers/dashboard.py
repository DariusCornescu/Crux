"""Dashboard payload — one block per instrument (GATE / STRIP / ALTI),
plus the Rail and a 14-day mood trend from Spotify listening data.

Returns demo data while the DB has no activities so the Android client
can be developed against the real payload shape.
"""
from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Activity, ActivityType, DailySummary, EffortMode
from app.schemas import AltiBlock, Conditions, DashboardOut, GateBlock, RailEntry, StripBlock

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


def _demo(week_start: date) -> DashboardOut:
    return DashboardOut(
        week=week_start.isocalendar().week,
        conditions=Conditions(sleep_min=432, resting_hr=52, mood_valence=0.64),
        rail=[
            RailEntry(day=week_start, mode=EffortMode.explosive, type=ActivityType.sprint,
                      duration_s=3600, best_split=6.98),
            RailEntry(day=week_start + timedelta(days=1), mode=EffortMode.aerobic,
                      type=ActivityType.easy_run, duration_s=2690, distance_m=8200),
            RailEntry(day=week_start + timedelta(days=2), mode=EffortMode.loaded,
                      type=ActivityType.ruck, duration_s=5400, vert_m=540),
            RailEntry(day=week_start + timedelta(days=4), mode=EffortMode.explosive,
                      type=ActivityType.sprint, duration_s=3000, best_split=7.11),
            RailEntry(day=week_start + timedelta(days=5), mode=EffortMode.aerobic,
                      type=ActivityType.easy_run, duration_s=4704, distance_m=14000),
            RailEntry(day=week_start + timedelta(days=6), mode=EffortMode.loaded,
                      type=ActivityType.hike, duration_s=7200, vert_m=410),
        ],
        gate=GateBlock(best_split=6.98, pb=6.91, session_note="60m fly ×3 · rest 8' · RPE 8",
                       splits=[7.04, 6.98, 7.02]),
        strip=StripBlock(week_km=26.2, long_run_km=14.0, z2_pct=74,
                         pace_trend=[334, 331, 328, 330, 326, 329, 336, 332, 330, 327, 331, 335, 338, 341]),
        alti=AltiBlock(vert_m=950, goal_m=2000, load_kg=18, carries=2),
    )


@router.get("/summary", response_model=DashboardOut)
def summary(db: Session = Depends(get_db)):
    today = date.today()
    week_start = today - timedelta(days=today.weekday())
    week_start_dt = datetime.combine(week_start, datetime.min.time(), tzinfo=timezone.utc)

    has_data = db.scalar(select(Activity.id).limit(1)) is not None
    if not has_data:
        return _demo(week_start)

    activities = db.scalars(
        select(Activity).where(Activity.start_time >= week_start_dt).order_by(Activity.start_time)
    ).all()

    rail: list[RailEntry] = []
    gate = GateBlock()
    strip = StripBlock()
    alti = AltiBlock()

    for a in activities:
        entry = RailEntry(day=a.start_time.date(), mode=a.mode, type=a.type, duration_s=a.duration_s)
        if a.mode == EffortMode.explosive:
            best = min(a.splits) if a.splits else None
            entry.best_split = best
            if best and (gate.best_split is None or best < gate.best_split):
                gate.best_split = best
                gate.splits = a.splits or []
                gate.session_note = a.name
        elif a.mode == EffortMode.aerobic:
            entry.distance_m = a.distance_m
            km = (a.distance_m or 0) / 1000
            strip.week_km = round(strip.week_km + km, 1)
            strip.long_run_km = max(strip.long_run_km, round(km, 1))
        else:
            entry.vert_m = a.elevation_gain_m
            alti.vert_m += a.elevation_gain_m or 0
            alti.carries += 1
            if a.load_kg:
                alti.load_kg = a.load_kg
        rail.append(entry)

    latest = db.scalars(select(DailySummary).order_by(DailySummary.day.desc()).limit(1)).first()
    conditions = Conditions(
        sleep_min=latest.sleep_duration_min if latest else None,
        resting_hr=latest.resting_hr if latest else None,
        mood_valence=latest.mood_valence if latest else None,
    )

    return DashboardOut(week=week_start.isocalendar().week, conditions=conditions,
                        rail=rail, gate=gate, strip=strip, alti=alti)
