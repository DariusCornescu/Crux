from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from datetime import date

from app import quotes
from app.database import get_db

router = APIRouter(prefix="/quote", tags=["quote"])


class QuoteOut(BaseModel):
    day: date
    text: str
    source: str


@router.get("/today", response_model=QuoteOut)
def today(db: Session = Depends(get_db)):
    row = quotes.get_today(db)
    return QuoteOut(day=row.day, text=row.text, source=row.source)
