from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel


class NoticeResponse(BaseModel):
    id: str
    title: str
    file_url: str
    uploaded_by: str
    ocr_status: str
    extracted_text: Optional[str] = None
    summary: Optional[str] = None
    checklist: Optional[list] = None
    ocr_confidence: Optional[float] = None
    distributed_to: Optional[list] = None
    distributed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class NoticeDistributeRequest(BaseModel):
    store_ids: List[str]
