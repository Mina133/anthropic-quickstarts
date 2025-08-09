from datetime import datetime
from sqlalchemy import Column, DateTime, ForeignKey, String, Text, JSON
from sqlalchemy.orm import relationship
from ..database import Base


class Message(Base):
    __tablename__ = "messages"

    id = Column(String(36), primary_key=True)
    session_id = Column(String(36), ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False)
    role = Column(String(20), nullable=False)  # user | assistant | system | tool
    content = Column(Text, nullable=True)
    content_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    session = relationship("Session", backref="messages")


