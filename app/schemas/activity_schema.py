from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime
from uuid import UUID
from app.models.activity_log import ActivityEventType


class ActivityLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    quote_id: UUID
    event_type: ActivityEventType
    description: Optional[str]
    performed_by: Optional[UUID]
    created_at: datetime
