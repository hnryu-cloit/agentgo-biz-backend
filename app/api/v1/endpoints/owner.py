from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.dependencies import get_current_user, require_roles
from app.db.database import get_db
from app.models.user import User
from app.models.action import Action
from app.models.store import Store
from app.schemas.action import ActionResponse, ActionUpdateRequest
from app.services.resource_metrics_service import ResourceMetricsService

router = APIRouter()


@router.get("/dashboard")
async def owner_dashboard(
    store_key: Optional[str] = Query(None, description="조회할 매장 키 (미입력 시 첫 번째 매장)"),
    current_user: User = Depends(require_roles(["store_owner", "hq_admin"])),
    db: AsyncSession = Depends(get_db),
):
    metrics_service = ResourceMetricsService(db)
    if not store_key:
        resource_stores = await metrics_service.get_store_options()
        store_key = resource_stores[0]["store_key"] if resource_stores else None
    metrics = await metrics_service.get_owner_dashboard_metrics(store_key=store_key)
    return metrics


@router.get("/customer-insights")
async def owner_customer_insights(
    store_key: Optional[str] = Query(None, description="조회할 매장 키 (미입력 시 첫 번째 매장)"),
    days: int = Query(90, ge=7, le=365, description="분석 기간 (일)"),
    current_user: User = Depends(require_roles(["store_owner", "hq_admin"])),
    db: AsyncSession = Depends(get_db),
):
    """도도포인트 기반 고객 방문 분석 (재방문율, 일별 트렌드 등)"""
    metrics_service = ResourceMetricsService(db)
    if not store_key:
        resource_stores = await metrics_service.get_store_options()
        store_key = resource_stores[0]["store_key"] if resource_stores else None
    if not store_key:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="사용 가능한 매장 데이터가 없습니다")
    return await metrics_service.get_dodo_customer_metrics(store_key=store_key, days=days)


@router.get("/actions", response_model=List[ActionResponse])
async def get_owner_actions(
    current_user: User = Depends(require_roles(["store_owner", "hq_admin"])),
    db: AsyncSession = Depends(get_db),
):
    store_id = current_user.store_id
    if not store_id and current_user.role != "hq_admin":
        return []

    query = select(Action).where(
        Action.store_id == store_id,
        Action.status == "pending",
    ).order_by(Action.priority).limit(3)

    result = await db.execute(query)
    return list(result.scalars().all())


@router.patch("/actions/{action_id}", response_model=ActionResponse)
async def update_owner_action(
    action_id: str,
    request: ActionUpdateRequest,
    current_user: User = Depends(require_roles(["store_owner", "hq_admin"])),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Action).where(Action.id == action_id))
    action = result.scalar_one_or_none()
    if not action:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Action not found")

    if current_user.role == "store_owner" and action.store_id != current_user.store_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    if request.status not in ["executed", "deferred", "ignored"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid status")

    action.status = request.status
    if request.defer_reason:
        action.defer_reason = request.defer_reason
    if request.status == "executed":
        action.executed_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(action)
    return action


@router.get("/qna/suggest")
async def suggest_qna(current_user: User = Depends(require_roles(["store_owner", "hq_admin"]))):
    return {
        "questions": [
            "오늘 매출이 어제보다 낮은 이유는 무엇인가요?",
            "이번 주 가장 잘 팔리는 메뉴는 무엇인가요?",
            "취소율을 낮추려면 어떻게 해야 하나요?",
            "피크 시간대 운영 효율을 높이는 방법은?",
            "단골 고객 이탈을 방지하는 방법은?",
        ]
    }

