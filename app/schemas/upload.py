from datetime import datetime, date
from typing import Optional, Any
from pydantic import BaseModel


class UploadJobCreateResponse(BaseModel):
    job_id: str
    status: str


class PipelineStages(BaseModel):
    normalize: str = "pending"
    kpi_aggregate: str = "pending"
    margin_guard: str = "pending"
    rfm: str = "pending"
    anomaly_detect: str = "pending"
    briefing_schedule: str = "pending"


class UploadJobResponse(BaseModel):
    id: str
    user_id: str
    store_id: str
    data_type: str
    original_filename: str
    file_path: str
    file_size_bytes: int
    status: str
    pipeline_stages: Optional[dict] = None
    error_detail: Optional[dict] = None
    quality_score: Optional[float] = None
    preview_rows: Optional[list] = None
    period_start: Optional[date] = None
    period_end: Optional[date] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class UploadMappingRequest(BaseModel):
    job_id: str
    store_id: str
    period_start: Optional[date] = None
    period_end: Optional[date] = None
