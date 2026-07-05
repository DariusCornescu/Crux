from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import ChatMessage
from app.schemas import ChatIn, ChatOut

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", response_model=ChatOut)
def chat(payload: ChatIn, db: Session = Depends(get_db)):
    """Build-order step 6: assemble data context + call the LLM.

    Skeleton stores the message and echoes a placeholder so the Android
    chat UI can be wired end-to-end first.
    """
    db.add(ChatMessage(role="user", content=payload.message))
    reply = "Chat is not wired to the LLM yet (build-order step 6)."
    db.add(ChatMessage(role="assistant", content=reply))
    db.commit()
    return ChatOut(reply=reply)
