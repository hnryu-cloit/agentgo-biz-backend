from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import OperationalError, ProgrammingError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import require_roles, verify_ai_service_token
from app.db.database import get_db
from app.models.user import User
from app.schemas.resource_data import (
    ResourceCatalogResponse,
    ResourceDatasetResponse,
    ResourceImportResponse,
)
from app.services.resource_data_service import ResourceDataService

router = APIRouter()


@router.get("/resource/catalog", response_model=ResourceCatalogResponse)
async def get_resource_catalog(
    current_user: User = Depends(require_roles(["hq_admin", "supervisor", "marketer"])),
    db: AsyncSession = Depends(get_db),
):
    service = ResourceDataService()
    return await service.list_catalog_from_db(db)


@router.get("/resource/datasets/{source_kind}/{store_key}", response_model=ResourceDatasetResponse)
async def get_resource_dataset(
    source_kind: str,
    store_key: str,
    limit: int = Query(50, ge=1, le=200),
    current_user: User = Depends(require_roles(["hq_admin", "supervisor", "marketer"])),
    db: AsyncSession = Depends(get_db),
):
    service = ResourceDataService()
    try:
        return await service.get_dataset_from_db(db=db, source_kind=source_kind, store_key=store_key, limit=limit)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.post("/resource/import", response_model=ResourceImportResponse)
async def import_resource_dataset(
    source_kind: str = Query(...),
    store_key: Optional[str] = Query(None),
    current_user: User = Depends(require_roles(["hq_admin"])),
    db: AsyncSession = Depends(get_db),
):
    service = ResourceDataService()
    try:
        imported_count = await service.import_dataset(db=db, source_kind=source_kind, store_key=store_key)
    except (OperationalError, ProgrammingError) as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Resource snapshot tables are not ready. Run database migrations first.",
        ) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    return ResourceImportResponse(
        source_kind=source_kind,
        store_key=store_key,
        imported_count=imported_count,
        message="Resource data import completed",
    )


@router.get("/ai/datasets/{source_kind}/{store_key}", response_model=ResourceDatasetResponse)
async def get_ai_dataset(
    source_kind: str,
    store_key: str,
    limit: int = Query(200, ge=1, le=1000),
    ai_token: str = Depends(verify_ai_service_token),
    db: AsyncSession = Depends(get_db),
):
    service = ResourceDataService()
    try:
        return await service.get_dataset_from_db(db=db, source_kind=source_kind, store_key=store_key, limit=limit)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
