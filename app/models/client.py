import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.database import Base


class Client(Base):
    __tablename__ = "clients"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    company_name = Column(String(200), nullable=False, index=True)
    contact_name = Column(String(150), nullable=False)
    email = Column(String(255), nullable=False)
    phone = Column(String(50))
    notes = Column(Text)
    tier = Column(String(50))
    industry = Column(String(100))
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    owner = relationship("User", back_populates="clients")
    quotes = relationship("Quote", back_populates="client", cascade="all, delete-orphan")