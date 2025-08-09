import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session as OrmSession

from ..database import get_db
from ..models.session import Session as SessionModel
from ..models.message import Message as MessageModel
from ..schemas import SessionCreate, SessionRead, ChatHistoryRead
from ..services.vm_manager import vm_manager
from ..services.event_store import event_store


router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.post("", response_model=SessionRead)
def create_session(payload: SessionCreate, db: OrmSession = Depends(get_db)):
    vm_info = vm_manager.create_vm()
    session = SessionModel(
        id=str(uuid.uuid4()),
        title=payload.title,
        metadata_json={**(payload.metadata or {}), "vm": vm_info},
        status="active",
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


@router.get("", response_model=list[SessionRead])
def list_sessions(db: OrmSession = Depends(get_db)):
    # latest first
    sessions = db.query(SessionModel).order_by(SessionModel.updated_at.desc()).all()
    return sessions


@router.post("/{session_id}/archive", response_model=SessionRead)
def archive_session(session_id: str, db: OrmSession = Depends(get_db)):
    session = db.get(SessionModel, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    # Stop per-session VM if present
    try:
        container_id = (session.metadata_json or {}).get("vm", {}).get("container_id")
        if container_id:
            vm_manager.stop_vm(container_id)
    except Exception:
        pass
    session.status = "archived"
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


@router.get("/{session_id}/events")
def list_session_events(session_id: str):
    # Returns stored live stream events (if MongoDB is configured)
    return event_store.list(session_id)

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



