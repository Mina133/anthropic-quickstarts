from fastapi import APIRouter, Depends, HTTPException
from fastapi import WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session as OrmSession

from ..database import get_db
from ..models.session import Session as SessionModel
from ..services.stream_manager import stream_manager


router = APIRouter(prefix="/sessions/{session_id}", tags=["stream"])


@router.websocket("/stream")
async def stream_session(websocket: WebSocket, session_id: str, db: OrmSession = Depends(get_db)):
    session = db.get(SessionModel, session_id)
    if not session:
        # WebSockets cannot raise HTTP errors after accept; deny early
        await websocket.close(code=4404)
        return

    await stream_manager.connect(session_id, websocket)
    try:
        while True:
            # Idle loop; outbound broadcast will drive data
            await asyncio.sleep(60)
    except WebSocketDisconnect:
        await stream_manager.disconnect(session_id, websocket)


