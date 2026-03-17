import os
import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.dependencies import get_current_user
from app.core.config import settings
from app.db.database import get_db
from app.models.user import User
from app.models.upload_job import UploadJob
from app.schemas.upload import UploadJobCreateResponse, UploadJobResponse, UploadMappingRequest
from app.services.resource_data_service import ResourceDataService, SOURCE_SPECS
from app.services.upload_service import UploadService

router = APIRouter()

ALLOWED_EXTENSIONS = {".csv", ".xlsx"}
MAX_SIZE_BYTES = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
LEGACY_DATA_TYPES = {"sales", "cost", "customer", "review"}
SUPPORTED_DATA_TYPES = LEGACY_DATA_TYPES | set(SOURCE_SPECS.keys())


@router.post("/upload", response_model=UploadJobCreateResponse, status_code=status.HTTP_201_CREATED)
async def upload_file(
    file: UploadFile = File(...),
    data_type: str = Query(..., description="sales/cost/customer/review/pos_daily_sales/bo_point_usage/receipt_listing/menu_lineup"),
    store_id: str = Query(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Validate extension
    _, ext = os.path.splitext(file.filename)
    if ext.lower() not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only CSV and XLSX files allowed")

    # Read file content
    content = await file.read()
    file_size = len(content)

    if file_size > MAX_SIZE_BYTES:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="File too large (max 100MB)")

    if data_type not in SUPPORTED_DATA_TYPES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid data_type")

    # Save file
    job_id = str(uuid.uuid4())
    user_dir = os.path.join(settings.UPLOAD_DIR, current_user.id)
    os.makedirs(user_dir, exist_ok=True)
    file_path = os.path.join(user_dir, f"{job_id}_{file.filename}")

    with open(file_path, "wb") as f:
        f.write(content)

    service = UploadService(db)
    job = await service.create_job(
        user_id=current_user.id,
        store_id=store_id,
        data_type=data_type,
        original_filename=file.filename,
        file_path=file_path,
        file_size_bytes=file_size,
    )

    if data_type in SOURCE_SPECS:
        parser = ResourceDataService()
        try:
            dataset = parser.get_dataset(source_kind=data_type, store_key=store_id, limit=10)
            job.preview_rows = dataset["rows"]
            job.period_start = dataset["summary"].get("date_start")
            job.period_end = dataset["summary"].get("date_end")
            job.error_detail = {
                "source_kind": data_type,
                "headers": dataset["headers"],
                "summary": dataset["summary"],
            }
            job.pipeline_stages = {
                "normalize": "completed",
                "kpi_aggregate": "pending",
                "margin_guard": "pending",
                "rfm": "pending",
                "anomaly_detect": "pending",
                "briefing_schedule": "pending",
            }
            await db.commit()
            await db.refresh(job)
        except ValueError:
            pass

    return UploadJobCreateResponse(job_id=job.id, status=job.status)


@router.get("/upload/jobs", response_model=List[UploadJobResponse])
async def list_upload_jobs(
    store_id: Optional[str] = Query(None),
    data_type: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    query = select(UploadJob)

    if current_user.role == "store_owner":
        query = query.where(UploadJob.user_id == current_user.id)
    elif current_user.role != "hq_admin":
        query = query.where(UploadJob.user_id == current_user.id)

    if store_id:
        query = query.where(UploadJob.store_id == store_id)
    if data_type:
        query = query.where(UploadJob.data_type == data_type)

    result = await db.execute(query.order_by(UploadJob.created_at.desc()))
    return list(result.scalars().all())


@router.get("/upload/jobs/{job_id}", response_model=UploadJobResponse)
async def get_upload_job(
    job_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(UploadJob).where(UploadJob.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    if current_user.role != "hq_admin" and job.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    return job


@router.post("/upload/jobs/{job_id}/retry", response_model=UploadJobResponse)
async def retry_upload_job(
    job_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(UploadJob).where(UploadJob.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    if current_user.role != "hq_admin" and job.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    if job.status != "failed":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only failed jobs can be retried")

    job.status = "pending"
    job.error_detail = None
    job.pipeline_stages = {
        "normalize": "pending",
        "kpi_aggregate": "pending",
        "margin_guard": "pending",
        "rfm": "pending",
        "anomaly_detect": "pending",
        "briefing_schedule": "pending",
    }
    await db.commit()
    await db.refresh(job)
    return job


@router.post("/mapping")
async def store_mapping(
    request: UploadMappingRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(UploadJob).where(UploadJob.id == request.job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    job.store_id = request.store_id
    if request.period_start:
        job.period_start = request.period_start
    if request.period_end:
        job.period_end = request.period_end

    await db.commit()
    await db.refresh(job)
    return {"message": "Mapping updated", "job_id": job.id}
