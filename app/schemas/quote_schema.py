from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from datetime import datetime
from uuid import UUID
from decimal import Decimal
from app.models.quote import QuoteStatus
from app.schemas.client_schema import ClientOut
from app.schemas.quote_item_schema import QuoteItemOut
from app.schemas.activity_schema import ActivityLogOut


class QuoteCreate(BaseModel):
    client_id: UUID
    validity_date: Optional[datetime] = None
    notes: Optional[str] = None
    internal_notes: Optional[str] = None
    terms: Optional[str] = None
    currency: str = "USD"
    tax_pct: Decimal = Decimal("0.00")
    adjustment: Decimal = Decimal("0.00")


class QuoteUpdate(BaseModel):
    client_id: Optional[UUID] = None
    validity_date: Optional[datetime] = None
    notes: Optional[str] = None
    internal_notes: Optional[str] = None
    terms: Optional[str] = None
    status: Optional[QuoteStatus] = None
    currency: Optional[str] = None
    tax_pct: Optional[Decimal] = None
    adjustment: Optional[Decimal] = None
    client_comment: Optional[str] = None


class QuoteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    quote_number: str
    parent_quote_id: Optional[UUID]
    version: int
    client_id: UUID
    created_by: UUID
    validity_date: Optional[datetime]
    notes: Optional[str]
    internal_notes: Optional[str]
    terms: Optional[str]
    status: QuoteStatus
    currency: str
    tax_pct: Decimal
    adjustment: Decimal
    public_token: str
    client_comment: Optional[str]
    created_at: datetime
    updated_at: datetime
    client: Optional[ClientOut] = None
    items: List[QuoteItemOut] = []
    activity_logs: List[ActivityLogOut] = []


class QuoteListOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    quote_number: str
    version: int
    status: QuoteStatus
    currency: str
    public_token: str
    client: Optional[ClientOut] = None
    created_at: datetime
    updated_at: datetime


class PublicQuoteRespond(BaseModel):
    action: str  # approved | changes_requested | rejected
    comment: Optional[str] = None


class SendQuoteRequest(BaseModel):
    custom_message: Optional[str] = None


class DashboardStats(BaseModel):
    total_active: int
    pending_approval: int
    drafts: int
    approved: int
    rejected: int
    total_value: Decimal


class ImportResult(BaseModel):
    created: int
    errors: List[str]
