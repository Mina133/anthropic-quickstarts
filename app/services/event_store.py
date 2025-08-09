from __future__ import annotations

from typing import Any, Dict, Optional

from ..config import get_settings

settings = get_settings()

try:
    from pymongo import MongoClient  # type: ignore
except Exception:  # pragma: no cover
    MongoClient = None  # type: ignore


class EventStore:
    def __init__(self):
        self.client = None
        self.coll = None
        if settings.mongodb_uri and MongoClient is not None:
            try:
                self.client = MongoClient(settings.mongodb_uri)
                self.coll = self.client[settings.mongodb_db]["session_events"]
                self.coll.create_index("session_id")
                self.coll.create_index("at")
            except Exception:
                self.client = None
                self.coll = None

    def append(self, session_id: str, event: Dict[str, Any]) -> None:
        if not self.coll:
            return
        doc = {"session_id": session_id, **event}
        try:
            self.coll.insert_one(doc)
        except Exception:
            pass

    def list(self, session_id: str, limit: int = 500) -> list[Dict[str, Any]]:
        if not self.coll:
            return []
        return list(self.coll.find({"session_id": session_id}).sort("at", 1).limit(limit))


event_store = EventStore()


