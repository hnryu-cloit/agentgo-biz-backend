from datetime import datetime, date
from typing import Optional
from pydantic import BaseModel


class ActionResponse(BaseModel):
    id: str
    store_id: str
    created_by: str
    title: str
    description: str
    category: str
    priority: str
    status: str
    defer_reason: Optional[str] = None
    ai_basis: Optional[str] = None
    expected_impact: Optional[str] = None
    due_date: Optional[date] = None
    executed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ActionUpdateRequest(BaseModel):
    status: str  # executed|deferred|ignored
    defer_reason: Optional[str] = None
