from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime
from uuid import UUID
from decimal import Decimal


class QuoteItemCreate(BaseModel):
    product_id: Optional[UUID] = None
    product_name: str
    description: Optional[str] = None
    size_capacity: Optional[str] = None
    color: Optional[str] = None
    quantity: int = 1
    unit_price: Decimal
    discount_pct: Decimal = Decimal("0.00")
    lead_time: Optional[str] = None
    sort_order: int = 0


class QuoteItemUpdate(BaseModel):
    product_name: Optional[str] = None
    description: Optional[str] = None
    size_capacity: Optional[str] = None
    color: Optional[str] = None
    quantity: Optional[int] = None
    unit_price: Optional[Decimal] = None
    discount_pct: Optional[Decimal] = None
    lead_time: Optional[str] = None
    logo_url: Optional[str] = None
    mockup_url: Optional[str] = None
    logo_x: Optional[float] = None
    logo_y: Optional[float] = None
    logo_scale: Optional[float] = None
    sort_order: Optional[int] = None


class MockupSaveRequest(BaseModel):
    logo_x: float
    logo_y: float
    logo_scale: float
    mockup_image_base64: str


class QuoteItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    quote_id: UUID
    product_id: Optional[UUID]
    product_name: str
    description: Optional[str]
    size_capacity: Optional[str]
    color: Optional[str]
    quantity: int
    unit_price: Decimal
    discount_pct: Decimal
    final_price: Optional[Decimal]
    lead_time: Optional[str]
    logo_url: Optional[str]
    mockup_url: Optional[str]
    logo_x: Optional[float]
    logo_y: Optional[float]
    logo_scale: Optional[float]
    sort_order: int
    created_at: datetime


class QuoteItemSummary(BaseModel):
    subtotal: Decimal
    total_discount_amount: Decimal
    grand_total: Decimal
    item_count: int
