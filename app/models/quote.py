import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, Integer, DateTime, ForeignKey, Enum as SAEnum, Numeric
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.database import Base
import enum


class QuoteStatus(str, enum.Enum):
    draft = "draft"
    sent = "sent"
    approved = "approved"
    changes_requested = "changes_requested"
    rejected = "rejected"


class Quote(Base):
    __tablename__ = "quotes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    quote_number = Column(String(30), unique=True, nullable=False, index=True)
    parent_quote_id = Column(UUID(as_uuid=True), ForeignKey("quotes.id"), nullable=True)
    version = Column(Integer, default=1, nullable=False)
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.id", ondelete="CASCADE"), nullable=False)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    validity_date = Column(DateTime, nullable=True)
    notes = Column(Text)
    internal_notes = Column(Text)
    terms = Column(Text)
    status = Column(SAEnum(QuoteStatus), default=QuoteStatus.draft, nullable=False)
    currency = Column(String(10), default="USD", nullable=False)
    tax_pct = Column(Numeric(5, 2), default=0)
    adjustment = Column(Numeric(10, 2), default=0)
    public_token = Column(String(36), unique=True, default=lambda: str(uuid.uuid4()), nullable=False)
    client_comment = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    client = relationship("Client", back_populates="quotes")
    owner = relationship("User", back_populates="quotes")
    items = relationship("QuoteItem", back_populates="quote", cascade="all, delete-orphan", order_by="QuoteItem.sort_order")
    activity_logs = relationship("ActivityLog", back_populates="quote", cascade="all, delete-orphan", order_by="ActivityLog.created_at.desc()")
    child_versions = relationship("Quote", foreign_keys=[parent_quote_id])
