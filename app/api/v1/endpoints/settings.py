from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.dependencies import get_current_user, require_roles
from app.db.database import get_db
from app.models.user import User
from app.models.store import Store
from app.schemas.user import UserResponse
from app.schemas.store import StoreResponse
from app.services.store_service import StoreService

router = APIRouter()


@router.get("/users", response_model=List[UserResponse])
async def settings_list_users(
    role: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    current_user: User = Depends(require_roles(["hq_admin"])),
    db: AsyncSession = Depends(get_db),
):
    query = select(User)
    if role:
        query = query.where(User.role == role)
    if is_active is not None:
        query = query.where(User.is_active == is_active)
    result = await db.execute(query)
    return list(result.scalars().all())


@router.get("/stores", response_model=List[StoreResponse])
async def settings_list_stores(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = StoreService(db)
    stores = await service.get_stores_for_user(current_user)
    return stores
