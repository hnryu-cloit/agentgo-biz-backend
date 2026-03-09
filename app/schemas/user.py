from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr


class UserResponse(BaseModel):
    id: str
    email: str
    name: str
    role: str
    store_id: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class UserCreateRequest(BaseModel):
    email: EmailStr
    name: str
    password: str
    role: str
    store_id: Optional[str] = None


class UserActiveRequest(BaseModel):
    is_active: bool
