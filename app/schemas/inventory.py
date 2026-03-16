from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List

class ItemMasterBase(BaseModel):
    name: str
    unit: str
    category: str
    safety_stock: float
    store_id: int

class ItemMasterCreate(ItemMasterBase):
    pass

class ItemMaster(ItemMasterBase):
    id: int
    class Config:
        from_attributes = True

class InventoryAuditCreate(BaseModel):
    item_id: int
    actual_stock: float
    store_id: int

class InventoryAudit(InventoryAuditCreate):
    id: int
    audit_date: datetime
    class Config:
        from_attributes = True

class InventoryLoss(BaseModel):
    item_id: int
    name: str
    loss_rate: float
    is_excess: bool
