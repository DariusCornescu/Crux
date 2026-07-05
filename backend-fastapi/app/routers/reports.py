from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Report
from app.schemas import ReportOut

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("", response_model=list[ReportOut])
def list_reports(limit: int = 20, db: Session = Depends(get_db)):
    return db.scalars(select(Report).order_by(Report.created_at.desc()).limit(limit)).all()
