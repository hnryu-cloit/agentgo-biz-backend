import uuid
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.core.dependencies import get_current_user, require_roles
from app.db.database import get_db
from app.models.user import User
from app.models.store import Store
from app.models.alert import Alert
from app.models.action import Action
from app.models.escalation import Escalation
from app.models.visit_log import VisitLog
from app.models.sales import SalesKpi
from app.schemas.visit_log import VisitLogCreateRequest, VisitLogResponse
from app.schemas.escalation import EscalationCreateRequest, EscalationResponse
from app.services.store_service import StoreService

router = APIRouter()


@router.get("/dashboard")
async def supervisor_dashboard(
    current_user: User = Depends(require_roles(["supervisor", "hq_admin"])),
    db: AsyncSession = Depends(get_db),
):
    service = StoreService(db)
    if current_user.role == "supervisor":
        store_ids = await service.get_assigned_store_ids(current_user.id)
    else:
        result = await db.execute(select(Store.id).where(Store.is_active == True))
        store_ids = [row[0] for row in result.fetchall()]

    p0_count = 0
    if store_ids:
        result = await db.execute(
            select(func.count(Alert.id)).where(
                Alert.store_id.in_(store_ids),
                Alert.severity == "P0",
                Alert.status != "resolved",
            )
        )
        p0_count = result.scalar() or 0

    return {
        "total_stores": len(store_ids),
        "p0_alert_count": p0_count,
        "avg_cancel_rate": 0.0,
        "low_margin_store_count": 0,
    }


@router.get("/stores")
async def list_supervisor_stores(
    sort_by: Optional[str] = Query(None),
    period: Optional[str] = Query(None),
    current_user: User = Depends(require_roles(["supervisor", "hq_admin"])),
    db: AsyncSession = Depends(get_db),
):
    service = StoreService(db)
    stores = await service.get_stores_for_user(current_user)

    store_list = []
    for store in stores:
        # Get latest alert count
        alert_result = await db.execute(
            select(func.count(Alert.id)).where(
                Alert.store_id == store.id,
                Alert.status != "resolved",
            )
        )
        alert_count = alert_result.scalar() or 0

        store_list.append({
            "id": store.id,
            "name": store.name,
            "region": store.region,
            "size": store.size,
            "is_active": store.is_active,
            "alert_count": alert_count,
            "risk_score": round(alert_count * 0.1, 2),
        })

    return store_list


@router.get("/stores/{store_id}/kpi")
async def get_store_kpi(
    store_id: str,
    current_user: User = Depends(require_roles(["supervisor", "hq_admin"])),
    db: AsyncSession = Depends(get_db),
):
    service = StoreService(db)
    if current_user.role == "supervisor":
        assigned = await service.get_assigned_store_ids(current_user.id)
        if store_id not in assigned:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    result = await db.execute(select(Store).where(Store.id == store_id))
    store = result.scalar_one_or_none()
    if not store:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Store not found")

    return {
        "store_id": store_id,
        "store_name": store.name,
        "revenue_today": 0.0,
        "revenue_yesterday": 0.0,
        "cancel_rate_today": 0.0,
        "cancel_rate_avg": 0.0,
        "avg_order_value_today": 0.0,
        "avg_order_value_avg": 0.0,
    }


@router.get("/actions")
async def get_action_compliance(
    current_user: User = Depends(require_roles(["supervisor", "hq_admin"])),
    db: AsyncSession = Depends(get_db),
):
    service = StoreService(db)
    stores = await service.get_stores_for_user(current_user)

    result = []
    for store in stores:
        actions_result = await db.execute(
            select(Action).where(Action.store_id == store.id)
        )
        actions = list(actions_result.scalars().all())
        total = len(actions)
        executed = sum(1 for a in actions if a.status == "executed")
        deferred = sum(1 for a in actions if a.status == "deferred")
        rate = round(executed / total, 2) if total > 0 else 0.0

        result.append({
            "store_id": store.id,
            "store_name": store.name,
            "total_actions": total,
            "executed": executed,
            "deferred": deferred,
            "execution_rate": rate,
        })

    return result


@router.post("/actions/{action_id}/escalate", response_model=EscalationResponse, status_code=status.HTTP_201_CREATED)
async def escalate_action(
    action_id: str,
    request: EscalationCreateRequest,
    current_user: User = Depends(require_roles(["supervisor", "hq_admin"])),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Action).where(Action.id == action_id))
    action = result.scalar_one_or_none()
    if not action:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Action not found")

    escalation = Escalation(
        id=str(uuid.uuid4()),
        store_id=request.store_id,
        reported_by=current_user.id,
        title=request.title,
        description=request.description,
        severity=request.severity,
        status="open",
    )
    db.add(escalation)
    await db.commit()
    await db.refresh(escalation)
    return escalation


@router.get("/visit-logs", response_model=List[VisitLogResponse])
async def list_visit_logs(
    current_user: User = Depends(require_roles(["supervisor", "hq_admin"])),
    db: AsyncSession = Depends(get_db),
):
    service = StoreService(db)
    stores = await service.get_stores_for_user(current_user)
    store_ids = [s.id for s in stores]

    if not store_ids:
        return []

    result = await db.execute(
        select(VisitLog).where(VisitLog.store_id.in_(store_ids)).order_by(VisitLog.visit_date.desc())
    )
    return list(result.scalars().all())


@router.post("/visit-logs", response_model=VisitLogResponse, status_code=status.HTTP_201_CREATED)
async def create_visit_log(
    request: VisitLogCreateRequest,
    current_user: User = Depends(require_roles(["supervisor", "hq_admin"])),
    db: AsyncSession = Depends(get_db),
):
    service = StoreService(db)
    if current_user.role == "supervisor":
        assigned = await service.get_assigned_store_ids(current_user.id)
        if request.store_id not in assigned:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not assigned to this store")

    log = VisitLog(
        id=str(uuid.uuid4()),
        store_id=request.store_id,
        supervisor_id=current_user.id,
        visit_date=request.visit_date,
        purpose=request.purpose,
        summary=request.summary,
        issues_found=request.issues_found,
        coaching_points=request.coaching_points,
        next_visit_date=request.next_visit_date,
    )
    db.add(log)
    await db.commit()
    await db.refresh(log)
    return log


@router.get("/visit-logs/{log_id}", response_model=VisitLogResponse)
async def get_visit_log(
    log_id: str,
    current_user: User = Depends(require_roles(["supervisor", "hq_admin"])),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(VisitLog).where(VisitLog.id == log_id))
    log = result.scalar_one_or_none()
    if not log:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Visit log not found")

    service = StoreService(db)
    if current_user.role == "supervisor":
        assigned = await service.get_assigned_store_ids(current_user.id)
        if log.store_id not in assigned:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    return log
