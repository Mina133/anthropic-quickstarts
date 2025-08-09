import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session as OrmSession

from ..database import get_db
from ..models.session import Session as SessionModel
from ..models.message import Message as MessageModel
from ..schemas import SessionCreate, SessionRead, ChatHistoryRead


router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.post("", response_model=SessionRead)
def create_session(payload: SessionCreate, db: OrmSession = Depends(get_db)):
    session = SessionModel(
        id=str(uuid.uuid4()),
        title=payload.title,
        metadata_json=payload.metadata or {},
        status="active",
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


@router.get("/{session_id}", response_model=ChatHistoryRead)
def get_session(session_id: str, db: OrmSession = Depends(get_db)):
    session = db.get(SessionModel, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    # Access messages relationship
    _ = session.messages  # ensure loaded
    return ChatHistoryRead(
        session=session,
        messages=session.messages,
    )



