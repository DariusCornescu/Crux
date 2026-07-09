from datetime import date

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app import mood
from app.database import get_db

router = APIRouter(prefix="/mood", tags=["mood"])


class MoodOut(BaseModel):
    day: date
    phrase: str
    source: str


@router.get("/current", response_model=MoodOut)
def current(db: Session = Depends(get_db)):
    row = mood.get_current(db)
    return MoodOut(day=row.day, phrase=row.phrase, source=row.source)
