from datetime import datetime
from typing import Any, List, Literal, Optional
from pydantic import BaseModel, Field


class SessionCreate(BaseModel):
    title: Optional[str] = None
    metadata: Optional[dict] = None


class SessionRead(BaseModel):
    id: str
    title: Optional[str]
    status: str
    created_at: datetime
    updated_at: datetime
    archived: bool
    last_agent_state: Optional[dict] = None
    metadata_json: Optional[dict] = None

    class Config:
        from_attributes = True


class MessageCreate(BaseModel):
    role: Literal["user", "system"] = "user"
    content: str = Field(..., min_length=1)


class MessageRead(BaseModel):
    id: str
    session_id: str
    role: str
    content: Optional[str]
    content_json: Optional[dict]
    created_at: datetime

    class Config:
        from_attributes = True


class ChatHistoryRead(BaseModel):
    session: SessionRead
    messages: List[MessageRead]


