import asyncio
from typing import Dict, List

from starlette.websockets import WebSocket


class StreamManager:
    def __init__(self):
        self._session_connections: Dict[str, List[WebSocket]] = {}
        self._lock = asyncio.Lock()

    async def connect(self, session_id: str, websocket: WebSocket):
        await websocket.accept()
        async with self._lock:
            self._session_connections.setdefault(session_id, []).append(websocket)

    async def disconnect(self, session_id: str, websocket: WebSocket):
        async with self._lock:
            if session_id in self._session_connections:
                conns = self._session_connections[session_id]
                if websocket in conns:
                    conns.remove(websocket)
                if not conns:
                    self._session_connections.pop(session_id, None)

    async def broadcast(self, session_id: str, message: dict):
        async with self._lock:
            conns = list(self._session_connections.get(session_id, []))
        for ws in conns:
            try:
                await ws.send_json(message)
            except Exception:
                # Best-effort cleanup
                await self.disconnect(session_id, ws)


stream_manager = StreamManager()


