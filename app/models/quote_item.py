import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, Integer, Float, DateTime, ForeignKey, Numeric
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.database import Base


class QuoteItem(Base):
    __tablename__ = "quote_items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    quote_id = Column(UUID(as_uuid=True), ForeignKey("quotes.id", ondelete="CASCADE"), nullable=False)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id", ondelete="SET NULL"), nullable=True)
    product_name = Column(String(200), nullable=False)
    description = Column(Text)
    size_capacity = Column(String(100))
    color = Column(String(100))
    quantity = Column(Integer, default=1, nullable=False)
    unit_price = Column(Numeric(10, 2), nullable=False)
    discount_pct = Column(Numeric(5, 2), default=0)
    final_price = Column(Numeric(10, 2))
    lead_time = Column(String(100))
    logo_url = Column(String(500))
    mockup_url = Column(String(500))
    logo_x = Column(Float, nullable=True)
    logo_y = Column(Float, nullable=True)
    logo_scale = Column(Float, nullable=True)
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    quote = relationship("Quote", back_populates="items")
    product = relationship("Product", back_populates="quote_items")
