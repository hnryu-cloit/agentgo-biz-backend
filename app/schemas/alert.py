from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class AlertResponse(BaseModel):
    id: str
    store_id: str
    alert_type: str
    severity: str
    title: str
    description: str
    detected_at: datetime
    anomaly_score: float
    status: str
    assigned_to: Optional[str] = None
    resolution_comment: Optional[str] = None
    resolved_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AlertUpdateRequest(BaseModel):
    status: str
    resolution_comment: Optional[str] = None
