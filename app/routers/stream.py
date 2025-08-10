import asyncio
from fastapi import APIRouter, HTTPException
from fastapi import WebSocket, WebSocketDisconnect

from ..database import SessionLocal
from ..models.session import Session as SessionModel
from ..services.stream_manager import stream_manager


router = APIRouter(prefix="/sessions/{session_id}", tags=["stream"])


@router.websocket("/stream")
async def stream_session(websocket: WebSocket, session_id: str):
    # Check session existence with short-lived DB session
    db = SessionLocal()
    try:
        session = db.get(SessionModel, session_id)
    finally:
        db.close()

    if not session:
        await websocket.close(code=4404)
        return

    await stream_manager.connect(session_id, websocket)
    try:
        while True:
            await asyncio.sleep(60)
    except WebSocketDisconnect:
        await stream_manager.disconnect(session_id, websocket)


