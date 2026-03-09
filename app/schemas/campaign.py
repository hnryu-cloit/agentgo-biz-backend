from datetime import datetime, date
from typing import Optional
from pydantic import BaseModel


class CampaignCreateRequest(BaseModel):
    name: str
    channel: str  # app_push/kakao/email
    target_segment: str
    offer_type: str  # coupon/points/discount
    offer_value: float
    message_template: str
    start_date: Optional[date] = None
    end_date: Optional[date] = None


class CampaignResponse(BaseModel):
    id: str
    name: str
    channel: str
    target_segment: str
    offer_type: str
    offer_value: float
    message_template: str
    status: str
    sent_count: int
    opened_count: int
    used_count: int
    revisit_count: int
    revenue_attributed: float
    created_by: str
    sent_at: Optional[datetime] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
