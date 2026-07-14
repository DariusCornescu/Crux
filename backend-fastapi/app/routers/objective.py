from datetime import date

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app import objective
from app.database import get_db

router = APIRouter(prefix="/objective", tags=["objective"])


class ObjectiveIn(BaseModel):
    name: str
    elevation_m: int | None = None
    target_date: date
    vert_goal_m: int
    start_date: date | None = None


class ObjectiveOut(BaseModel):
    name: str
    elevation_m: int | None
    target_date: date
    vert_goal_m: int
    start_date: date
    banked_m: int
    days_to_go: int


def _out(db: Session, obj) -> ObjectiveOut:
    return ObjectiveOut(
        name=obj.name, elevation_m=obj.elevation_m, target_date=obj.target_date,
        vert_goal_m=obj.vert_goal_m, start_date=obj.start_date,
        banked_m=objective.banked_m(db, obj), days_to_go=objective.days_to_go(obj),
    )


@router.get("/current", response_model=ObjectiveOut | None)
def current(db: Session = Depends(get_db)):
    obj = objective.get_active(db)
    return _out(db, obj) if obj else None


@router.post("", response_model=ObjectiveOut)
def upsert(body: ObjectiveIn, db: Session = Depends(get_db)):
    obj = objective.upsert(db, name=body.name, target_date=body.target_date,
                           vert_goal_m=body.vert_goal_m, elevation_m=body.elevation_m,
                           start_date=body.start_date)
    return _out(db, obj)
