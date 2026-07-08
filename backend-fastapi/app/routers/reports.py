from datetime import datetime, time, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import report_generator
from app.database import get_db
from app.models import Activity, DailySummary, EffortMode, Report
from app.schemas import MetricDay, ReportGenerateIn, ReportMetricsOut, ReportOut

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("", response_model=list[ReportOut])
def list_reports(limit: int = 20, db: Session = Depends(get_db)):
    return db.scalars(select(Report).order_by(Report.created_at.desc()).limit(limit)).all()


@router.get("/{report_id}", response_model=ReportOut)
def get_report(report_id: int, db: Session = Depends(get_db)):
    report = db.get(Report, report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="report not found")
    return report


@router.post("/generate", response_model=ReportOut)
def generate(payload: ReportGenerateIn | None = None, db: Session = Depends(get_db)):
    """Manual trigger — the same code path the Monday Celery beat runs."""
    week_start = payload.week_start if payload else None
    return report_generator.generate_weekly_report(db, week_start=week_start)


@router.get("/{report_id}/metrics", response_model=ReportMetricsOut)
def report_metrics(report_id: int, db: Session = Depends(get_db)):
    """Per-day km/vert/mood/sessions for a report's period — Android mini-charts."""
    report = db.get(Report, report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="report not found")

    start_dt = datetime.combine(report.period_start, time.min, tzinfo=timezone.utc)
    end_dt = datetime.combine(report.period_end + timedelta(days=1), time.min, tzinfo=timezone.utc)
    activities = db.scalars(select(Activity).where(
        Activity.start_time >= start_dt, Activity.start_time < end_dt)).all()
    summaries = {s.day: s for s in db.scalars(select(DailySummary).where(
        DailySummary.day >= report.period_start, DailySummary.day <= report.period_end)).all()}

    days = []
    d = report.period_start
    while d <= report.period_end:
        day_acts = [a for a in activities if a.start_time.date() == d]
        days.append(MetricDay(
            day=d,
            km=round(sum((a.distance_m or 0) / 1000 for a in day_acts
                         if a.mode == EffortMode.aerobic), 2),
            vert_m=round(sum(a.elevation_gain_m or 0 for a in day_acts
                             if a.mode == EffortMode.loaded), 1),
            mood_valence=summaries[d].mood_valence if d in summaries else None,
            sessions=len(day_acts),
        ))
        d += timedelta(days=1)
    return ReportMetricsOut(days=days)
