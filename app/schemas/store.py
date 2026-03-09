from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class StoreResponse(BaseModel):
    id: str
    name: str
    region: str
    address: str
    size: str
    open_time: Optional[str] = None
    close_time: Optional[str] = None
    break_start: Optional[str] = None
    break_end: Optional[str] = None
    seats: Optional[int] = None
    service_type: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class StoreUpdateRequest(BaseModel):
    name: Optional[str] = None
    region: Optional[str] = None
    address: Optional[str] = None
    size: Optional[str] = None
    open_time: Optional[str] = None
    close_time: Optional[str] = None
    break_start: Optional[str] = None
    break_end: Optional[str] = None
    seats: Optional[int] = None
    service_type: Optional[str] = None
    is_active: Optional[bool] = None
