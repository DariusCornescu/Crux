from datetime import date

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app import reflection
from app.database import get_db

router = APIRouter(prefix="/reflection", tags=["reflection"])


class ReflectionOut(BaseModel):
    day: date
    text: str
    source: str
    author: str = "CRUX"   # the reflection is Crux's own voice


@router.get("/today", response_model=ReflectionOut)
def today(db: Session = Depends(get_db)):
    row = reflection.get_today(db)
    return ReflectionOut(day=row.day, text=row.text, source=row.source)
