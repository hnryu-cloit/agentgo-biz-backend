from app.services.internal_ai_service import InternalAiService
from app.services.resource_data_service import ResourceDataService
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
from app.services.resource_metrics_service import ResourceMetricsService
from app.services.store_service import StoreService

router = APIRouter()


@router.get("/dashboard")
async def supervisor_dashboard(
    current_user: User = Depends(require_roles(["supervisor", "hq_admin"])),
    db: AsyncSession = Depends(get_db),
):
    metrics_service = ResourceMetricsService(db)
    return await metrics_service.get_supervisor_summary()


@router.get("/stores")
async def list_supervisor_stores(
    sort_by: Optional[str] = Query(None),
    period: Optional[str] = Query(None),
    current_user: User = Depends(require_roles(["supervisor", "hq_admin"])),
    db: AsyncSession = Depends(get_db),
):
    metrics_service = ResourceMetricsService(db)
    return await metrics_service.get_supervisor_store_rows()


@router.get("/stores/{store_id}/kpi")
async def get_store_kpi(
    store_id: str,
    current_user: User = Depends(require_roles(["supervisor", "hq_admin"])),
    db: AsyncSession = Depends(get_db),
):
    metrics_service = ResourceMetricsService(db)
    dashboard = await metrics_service.get_owner_dashboard_metrics(store_key=store_id)
    receipt_snapshot = await metrics_service.get_receipt_snapshot(store_key=store_id)
    customer_insights = await metrics_service.get_dodo_customer_metrics(store_key=store_id, days=30)
    return {
        "store_id": store_id,
        "store_name": dashboard["store_name"],
        "revenue_today": dashboard["today_revenue"],
        "revenue_yesterday": max(dashboard["today_revenue"] - dashboard["revenue_vs_yesterday"], 0.0),
        "cancel_rate_today": dashboard["cancel_rate"],
        "cancel_rate_avg": dashboard["cancel_rate"],
        "avg_order_value_today": dashboard["avg_order_value"],
        "avg_order_value_avg": dashboard["avg_order_value"],
        "receipt_count": receipt_snapshot.get("receipt_count", 0),
        "payment_total": receipt_snapshot.get("payment_total", 0.0),
        "sales_date": receipt_snapshot.get("sales_date"),
        "customer_insights": {
            "unique_customers_30d": customer_insights["unique_customers"],
            "return_rate": customer_insights["return_rate"],
            "recent_7d_visits": customer_insights["recent_7d_visits"],
            "visit_trend_delta_pct": customer_insights["visit_trend_delta_pct"],
            "earn_count": customer_insights["earn_count"],
        },
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

@router.get("/stores/{store_id}/analysis")
async def analyze_supervisor_store(
    store_id: str,
    current_user: User = Depends(require_roles(["supervisor", "hq_admin"])),
    db: AsyncSession = Depends(get_db),
):
    """SV 전용: 특정 매장에 대한 AI 심층 분석 (이슈/코칭포인트 도출)"""
    ai_service = InternalAiService()
    data_service = ResourceDataService(db)
    
    # 분석에 필요한 매장 데이터 취합
    sales_data = await data_service.get_dataset("pos_daily_sales", store_key=store_id, limit=50)
    receipt_data = await data_service.get_dataset("receipt_listing", store_key=store_id, limit=50)
    lineup_data = await data_service.get_dataset("menu_lineup", limit=50)
    
    # AI 엔진 다중 분석 호출
    try:
        menu_analysis = await ai_service.get_menu_analysis(sales_data, lineup_data)
        anomaly_analysis = await ai_service.get_anomaly_analysis(receipt_data)
        
        # SV 코칭 포인트 생성 (AI 결과 기반)
        coaching_points = []
        if anomaly_analysis.get("summary", {}).get("anomaly_score_max", 0) > 1.5:
            coaching_points.append("비정상 취소 패턴 감지에 따른 영수증 관리 프로세스 점검 필요")
        
        dogs_count = menu_analysis.get("summary", {}).get("dog_count", 0)
        if dogs_count > 0:
            coaching_points.append(f"수익성 하위 메뉴({dogs_count}건) 삭제 및 시그니처 메뉴 노출 강화 지도")
            
        return {
            "store_id": store_id,
            "ai_coaching_points": coaching_points or ["특이사항 없음. 현재 운영 품질 유지 지도"],
            "risk_analysis": anomaly_analysis,
            "menu_strategy": menu_analysis,
            "generated_at": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI Analysis Failed: {str(e)}")
