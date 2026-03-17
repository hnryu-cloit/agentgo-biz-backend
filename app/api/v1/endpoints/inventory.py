from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import require_roles
from app.db.database import get_db
from app.models.resource_data import MenuLineupSnapshot
from app.models.user import User
from app.schemas.inventory import ItemMaster, ItemMasterCreate, InventoryAudit, InventoryAuditCreate, InventoryLoss
from app.services.resource_operations_service import ResourceOperationsService

router = APIRouter()


@router.get("/menu-costs")
async def get_menu_costs(
    store_key: str = Query(..., description="매장 키 (예: 크리스탈제이드)"),
    category: Optional[str] = Query(None),
    current_user: User = Depends(require_roles(["store_owner", "hq_admin", "supervisor"])),
    db: AsyncSession = Depends(get_db),
):
    """메뉴 라인업 기반 원가 항목 조회 (StockTakePage용)"""
    q = select(MenuLineupSnapshot).where(
        MenuLineupSnapshot.store_key == store_key,
        MenuLineupSnapshot.menu_name.isnot(None),
        MenuLineupSnapshot.sales_price.isnot(None),
    )
    if category:
        q = q.where(MenuLineupSnapshot.menu_category == category)
    rows = list((await db.execute(q.order_by(MenuLineupSnapshot.row_number))).scalars().all())

    return {
        "store_key": store_key,
        "item_count": len(rows),
        "items": [
            {
                "id": row.id,
                "menu_name": row.menu_name,
                "menu_category": row.menu_category,
                "sales_price": row.sales_price,
                "cost_amount": row.cost_amount,
                "cost_rate": row.cost_rate,
            }
            for row in rows
        ],
    }


@router.get('/items', response_model=List[ItemMaster])
async def get_items(store_id: str = Query(...)):
    service = ResourceOperationsService()
    return [ItemMaster(**item) for item in service.get_inventory_items(store_id)]


@router.post('/items', response_model=ItemMaster)
async def create_item(item: ItemMasterCreate):
    return ItemMaster(id=3, **item.model_dump())


@router.post('/audit', response_model=InventoryAudit)
async def create_audit(audit: InventoryAuditCreate):
    return InventoryAudit(id=1, audit_date=datetime.utcnow(), **audit.model_dump())


@router.get('/theoretical')
async def get_theoretical_stock(store_id: str = Query(...), item_id: Optional[int] = Query(None)):
    service = ResourceOperationsService()
    rows = service.get_theoretical_inventory(store_id)
    if item_id is not None:
        rows = [row for row in rows if row["item_id"] == item_id]
    return rows


@router.get('/summary', response_model=List[InventoryLoss])
async def get_inventory_summary(store_id: str = Query(...), month: Optional[str] = Query(None)):
    service = ResourceOperationsService()
    return [InventoryLoss(**item) for item in service.get_inventory_summary(store_id)]
