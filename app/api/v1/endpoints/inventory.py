from fastapi import APIRouter, Depends, HTTPException
from typing import List, Any
from app.schemas.inventory import ItemMaster, ItemMasterCreate, InventoryAudit, InventoryAuditCreate, InventoryLoss
from datetime import datetime

router = APIRouter()

@router.get('/items', response_model=List[ItemMaster])
async def get_items(store_id: int):
    # Mock data
    return [
        ItemMaster(id=1, name='연어', unit='kg', category='식재료', safety_stock=5.0, store_id=store_id),
        ItemMaster(id=2, name='와사비', unit='kg', category='소스', safety_stock=1.0, store_id=store_id)
    ]

@router.post('/items', response_model=ItemMaster)
async def create_item(item: ItemMasterCreate):
    return ItemMaster(id=3, **item.model_dump())

@router.post('/audit', response_model=InventoryAudit)
async def create_audit(audit: InventoryAuditCreate):
    return InventoryAudit(id=1, audit_date=datetime.utcnow(), **audit.model_dump())

@router.get('/theoretical')
async def get_theoretical_stock(store_id: int, item_id: int):
    return {'item_id': item_id, 'store_id': store_id, 'theoretical_stock': 12.5, 'calculated_at': datetime.utcnow()}

@router.get('/summary', response_model=List[InventoryLoss])
async def get_inventory_summary(store_id: int, month: str):
    return [
        InventoryLoss(item_id=1, name='연어', loss_rate=0.05, is_excess=False),
        InventoryLoss(item_id=2, name='와사비', loss_rate=-0.02, is_excess=True)
    ]
