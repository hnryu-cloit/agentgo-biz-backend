from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class EscalationCreateRequest(BaseModel):
    store_id: str
    title: str
    description: str
    severity: str  # P0/P1/P2


class EscalationResponse(BaseModel):
    id: str
    store_id: str
    reported_by: str
    title: str
    description: str
    severity: str
    status: str
    acknowledged_by: Optional[str] = None
    acknowledged_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
