from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime
from uuid import UUID


class ClientCreate(BaseModel):
    company_name: str
    contact_name: str
    email: EmailStr
    phone: Optional[str] = None
    notes: Optional[str] = None
    tier: Optional[str] = None
    industry: Optional[str] = None


class ClientUpdate(BaseModel):
    company_name: Optional[str] = None
    contact_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    notes: Optional[str] = None
    tier: Optional[str] = None
    industry: Optional[str] = None


class ClientOut(BaseModel):
    id: UUID
    company_name: str
    contact_name: str
    email: str
    phone: Optional[str]
    notes: Optional[str]
    tier: Optional[str]
    industry: Optional[str]
    created_by: UUID
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}