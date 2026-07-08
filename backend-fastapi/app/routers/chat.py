from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import chat_service
from app.database import get_db
from app.models import ChatMessage
from app.schemas import ChatIn, ChatMessageOut, ChatOut

router = APIRouter(prefix="/chat", tags=["chat"])


@router.get("/history", response_model=list[ChatMessageOut])
def history(limit: int = 50, db: Session = Depends(get_db)):
    rows = db.scalars(
        select(ChatMessage).order_by(ChatMessage.created_at.desc(), ChatMessage.id.desc()).limit(limit)
    ).all()
    return list(reversed(rows))  # oldest first for the UI


@router.post("", response_model=ChatOut)
def chat(payload: ChatIn, db: Session = Depends(get_db)):
    return ChatOut(reply=chat_service.send_message(db, payload.message))


@router.delete("/history")
def clear_history(db: Session = Depends(get_db)):
    deleted = db.query(ChatMessage).delete()
    db.commit()
    return {"deleted": deleted}
