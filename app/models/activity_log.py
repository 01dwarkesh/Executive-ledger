import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.database import Base
import enum


class ActivityEventType(str, enum.Enum):
    quote_created = "quote_created"
    quote_sent = "quote_sent"
    client_opened = "client_opened"
    client_approved = "client_approved"
    client_rejected = "client_rejected"
    client_changes_requested = "client_changes_requested"
    version_created = "version_created"
    updated = "updated"


class ActivityLog(Base):
    __tablename__ = "activity_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    quote_id = Column(UUID(as_uuid=True), ForeignKey("quotes.id", ondelete="CASCADE"), nullable=False)
    event_type = Column(SAEnum(ActivityEventType), nullable=False)
    description = Column(String(500), nullable=True)
    performed_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    quote = relationship("Quote", back_populates="activity_logs")
    performer = relationship("User", foreign_keys=[performed_by])
