from datetime import date

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import quotes
from app.database import get_db
from app.models import DailyQuote

router = APIRouter(prefix="/quote", tags=["quote"])


class QuoteOut(BaseModel):
    day: date
    text: str
    source: str
    author: str | None = None


@router.get("/today", response_model=QuoteOut)
def today(db: Session = Depends(get_db)):
    row = quotes.get_today(db)
    return QuoteOut(day=row.day, text=row.text, source=row.source, author=row.author)


@router.get("/archive", response_model=list[QuoteOut])
def archive(limit: int = Query(30, ge=1, le=90), db: Session = Depends(get_db)):
    """Past daily quotes, newest first — the scrollable Philosophy-zone archive."""
    rows = db.scalars(
        select(DailyQuote).order_by(DailyQuote.day.desc()).limit(limit)
    ).all()
    return [QuoteOut(day=r.day, text=r.text, source=r.source, author=r.author) for r in rows]
