from datetime import datetime, date
from typing import Optional, List
from pydantic import BaseModel


class VisitLogCreateRequest(BaseModel):
    store_id: str
    visit_date: date
    purpose: str
    summary: Optional[str] = None
    issues_found: Optional[List[str]] = None
    coaching_points: Optional[List[str]] = None
    next_visit_date: Optional[date] = None


class VisitLogResponse(BaseModel):
    id: str
    store_id: str
    supervisor_id: str
    visit_date: date
    purpose: str
    summary: Optional[str] = None
    issues_found: Optional[list] = None
    coaching_points: Optional[list] = None
    next_visit_date: Optional[date] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
