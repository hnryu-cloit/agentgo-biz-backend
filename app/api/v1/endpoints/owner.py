from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.core.dependencies import get_current_user, require_roles
from app.db.database import get_db
from app.models.user import User
from app.models.action import Action
from app.models.sales import SalesKpi
from app.models.store import Store
from app.schemas.action import ActionResponse, ActionUpdateRequest

router = APIRouter()


@router.get("/dashboard")
async def owner_dashboard(
    current_user: User = Depends(require_roles(["store_owner", "hq_admin"])),
    db: AsyncSession = Depends(get_db),
):
    store_id = current_user.store_id
    if not store_id and current_user.role != "hq_admin":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No store assigned")

    # Get store name
    store_name = "Unknown Store"
    if store_id:
        result = await db.execute(select(Store).where(Store.id == store_id))
        store = result.scalar_one_or_none()
        if store:
            store_name = store.name

    # Get today's KPI (mock aggregate if no data)
    today = datetime.now(timezone.utc).date()
    kpi_result = await db.execute(
        select(SalesKpi).where(
            SalesKpi.store_id == store_id,
            SalesKpi.date == today,
            SalesKpi.hour == None,
        )
    ) if store_id else None

    kpi = kpi_result.scalar_one_or_none() if kpi_result else None

    # Hourly trend
    hourly_result = await db.execute(
        select(SalesKpi).where(
            SalesKpi.store_id == store_id,
            SalesKpi.date == today,
            SalesKpi.hour != None,
        ).order_by(SalesKpi.hour)
    ) if store_id else None

    hourly_data = []
    if hourly_result:
        for row in hourly_result.scalars().all():
            hourly_data.append({"hour": row.hour, "revenue": row.revenue})

    return {
        "store_name": store_name,
        "today_revenue": kpi.revenue if kpi else 0.0,
        "revenue_vs_yesterday": 0.0,
        "transaction_count": kpi.transaction_count if kpi else 0,
        "avg_order_value": kpi.avg_order_value if kpi else 0.0,
        "cancel_rate": kpi.cancel_rate if kpi else 0.0,
        "peak_hour": None,
        "kpi_trend": hourly_data,
    }


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


