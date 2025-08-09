import uuid
from datetime import datetime
from sqlalchemy import Column, DateTime, String, Boolean, JSON
from ..database import Base


def guid_column(primary_key: bool = False):
    # Use String for compatibility across SQLite/Postgres
    return Column(String(36), primary_key=primary_key, default=lambda: str(uuid.uuid4()))


class Session(Base):
    __tablename__ = "sessions"

    id = guid_column(primary_key=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    title = Column(String(255), nullable=True)
    status = Column(String(50), default="active", nullable=False)
    last_agent_state = Column(JSON, nullable=True)
    metadata_json = Column(JSON, nullable=True)
    archived = Column(Boolean, default=False, nullable=False)


