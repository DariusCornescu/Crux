from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app import readiness
from app.database import get_db

router = APIRouter(prefix="/readiness", tags=["readiness"])


class ReadinessOut(BaseModel):
    score: int
    label: str          # READY | EASY | REST | LOW DATA
    low_data: bool
    sleep_min: int | None = None
    resting_hr: int | None = None
    training_load: float | None = None


@router.get("/today", response_model=ReadinessOut)
def today(db: Session = Depends(get_db)):
    return readiness.compute(db)
