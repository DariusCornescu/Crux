from datetime import date

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app import training
from app.database import get_db

router = APIRouter(prefix="/training", tags=["training"])


class TrainingDay(BaseModel):
    day: date
    mode: str | None
    minutes: int


class TrainingGridOut(BaseModel):
    days: list[TrainingDay]      # oldest -> newest, dense (empty days have mode=null)
    total_sessions: int
    active_days: int


@router.get("/grid", response_model=TrainingGridOut)
def grid(weeks: int = Query(20, ge=1, le=53), db: Session = Depends(get_db)):
    return training.grid(db, weeks)
