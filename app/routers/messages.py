import uuid
import asyncio
from typing import Dict, List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session as OrmSession

from ..database import get_db
from ..models.session import Session as SessionModel
from ..models.message import Message as MessageModel
from ..schemas import MessageCreate, MessageRead
from ..services.stream_manager import stream_manager
from ..services.agent_runner import run_agent_for_new_user_message


router = APIRouter(prefix="/sessions/{session_id}/messages", tags=["messages"])


def build_anthropic_history(db_messages: List[MessageModel]) -> List[Dict]:
    history: List[Dict] = []
    for m in db_messages:
        if m.role == "user":
            history.append({"role": "user", "content": m.content or ""})
        elif m.role in ("assistant", "tool"):
            # We store assistant content as plain text or JSON snapshots
            assistant_content = m.content or ("" if not m.content_json else str(m.content_json))
            history.append({"role": "assistant", "content": assistant_content})
    return history


@router.post("", response_model=MessageRead)
async def send_message(session_id: str, payload: MessageCreate, db: OrmSession = Depends(get_db)):
    session = db.get(SessionModel, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    user_message = MessageModel(
        id=str(uuid.uuid4()),
        session_id=session_id,
        role="user",
        content=payload.content,
    )
    db.add(user_message)
    db.commit()
    db.refresh(user_message)

    # Stream to websockets that a user message arrived
    await stream_manager.broadcast(session_id, {
        "type": "user_message",
        "at": user_message.created_at.isoformat(),
        "message": {"id": user_message.id, "content": user_message.content},
    })

    # Build Anthropic history from DB
    db.refresh(session)
    history = build_anthropic_history(session.messages)

    async def handle_stream():
        await run_agent_for_new_user_message(db, session, user_message)
    asyncio.create_task(handle_stream())

    return user_message


