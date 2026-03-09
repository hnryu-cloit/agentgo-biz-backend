from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.dependencies import get_current_user
from app.db.database import get_db
from app.models.user import User
from app.models.store import Store
from app.schemas.store import StoreResponse, StoreUpdateRequest
from app.services.store_service import StoreService

router = APIRouter()


@router.get("/", response_model=List[StoreResponse])
async def list_stores(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = StoreService(db)
    stores = await service.get_stores_for_user(current_user)
    return stores


@router.get("/{store_id}", response_model=StoreResponse)
async def get_store(
    store_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = StoreService(db)
    allowed_stores = await service.get_stores_for_user(current_user)
    allowed_ids = {s.id for s in allowed_stores}

    if store_id not in allowed_ids:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied to this store")

    result = await db.execute(select(Store).where(Store.id == store_id))
    store = result.scalar_one_or_none()
    if not store:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Store not found")
    return store


@router.patch("/{store_id}", response_model=StoreResponse)
async def update_store(
    store_id: str,
    request: StoreUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if current_user.role not in ["hq_admin", "supervisor"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    service = StoreService(db)
    if current_user.role == "supervisor":
        assigned_ids = await service.get_assigned_store_ids(current_user.id)
        if store_id not in assigned_ids:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not assigned to this store")

    result = await db.execute(select(Store).where(Store.id == store_id))
    store = result.scalar_one_or_none()
    if not store:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Store not found")

    update_data = request.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(store, key, value)

    await db.commit()
    await db.refresh(store)
    return store
