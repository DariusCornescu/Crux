from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import report_generator
from app.database import get_db
from app.models import Report
from app.schemas import ReportGenerateIn, ReportOut

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
