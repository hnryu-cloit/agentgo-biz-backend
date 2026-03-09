from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class ReportGenerateRequest(BaseModel):
    report_type: str  # owner_daily/hq_weekly/sv_visit
    store_id: Optional[str] = None
    period_label: str


class ReportResponse(BaseModel):
    id: str
    report_type: str
    store_id: Optional[str] = None
    created_by: str
    title: str
    status: str
    file_url: Optional[str] = None
    period_label: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
