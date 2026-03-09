import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.dependencies import get_current_user
from app.db.database import get_db
from app.models.user import User
from app.models.report import Report
from app.schemas.report import ReportGenerateRequest, ReportResponse

router = APIRouter()


@router.get("/", response_model=List[ReportResponse])
async def list_reports(
    report_type: Optional[str] = Query(None),
    store_id: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    query = select(Report)
    if report_type:
        query = query.where(Report.report_type == report_type)
    if store_id:
        query = query.where(Report.store_id == store_id)

    if current_user.role == "store_owner":
        query = query.where(Report.store_id == current_user.store_id)

    result = await db.execute(query.order_by(Report.created_at.desc()))
    return list(result.scalars().all())


@router.post("/generate", response_model=ReportResponse)
async def generate_report(
    request: ReportGenerateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    report_id = str(uuid.uuid4())
    report = Report(
        id=report_id,
        report_type=request.report_type,
        store_id=request.store_id,
        created_by=current_user.id,
        title=f"{request.report_type} - {request.period_label}",
        status="completed",  # Mock: immediately complete
        file_url=f"/reports/{report_id}.pdf",
        period_label=request.period_label,
    )
    db.add(report)
    await db.commit()
    await db.refresh(report)
    return report
