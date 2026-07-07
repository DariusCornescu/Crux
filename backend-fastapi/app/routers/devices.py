from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import DeviceToken
from app.schemas import DeviceRegisterIn

router = APIRouter(prefix="/devices", tags=["devices"])


@router.post("", status_code=201)
def register(payload: DeviceRegisterIn, db: Session = Depends(get_db)) -> dict:
    """Idempotent FCM token registration (the app re-registers on refresh)."""
    token = db.scalar(select(DeviceToken).where(DeviceToken.token == payload.token))
    if token is None:
        db.add(DeviceToken(token=payload.token, platform=payload.platform))
        db.commit()
    return {"status": "ok"}
