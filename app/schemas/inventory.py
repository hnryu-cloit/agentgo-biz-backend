from pydantic import BaseModel, ConfigDict
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
    model_config = ConfigDict(from_attributes=True)

    id: int

class InventoryAuditCreate(BaseModel):
    item_id: int
    actual_stock: float
    store_id: int

class InventoryAudit(InventoryAuditCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int
    audit_date: datetime

class InventoryLoss(BaseModel):
    item_id: int
    name: str
    loss_rate: float
    is_excess: bool
