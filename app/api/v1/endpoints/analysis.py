from datetime import timedelta
from statistics import mean
from typing import Any, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import require_roles
from app.db.database import get_db
from app.models.resource_data import DodoPointSnapshot, PosDailySalesSnapshot
from app.models.user import User
from app.services.resource_metrics_service import ResourceMetricsService
from app.services.store_intelligence_service import StoreIntelligenceService

router = APIRouter()


@router.get("/store-intelligence")
async def store_intelligence(
    store_key: Optional[str] = Query(None),
    current_user: User = Depends(require_roles(["store_owner", "hq_admin", "supervisor", "marketer"])),
    db: AsyncSession = Depends(get_db),
):
    service = StoreIntelligenceService(db)
    return await service.build_store_intelligence(store_key=store_key)


@router.get("/roi")
async def promo_roi(
    store_id: Optional[str] = Query(None),
    current_user: User = Depends(require_roles(["marketer", "hq_admin"])),
    db: AsyncSession = Depends(get_db),
):
    latest_date_query = select(func.max(PosDailySalesSnapshot.sales_date))
    if store_id:
        latest_date_query = latest_date_query.where(PosDailySalesSnapshot.store_key == store_id)
    latest_date = (await db.execute(latest_date_query)).scalar_one_or_none()

    if latest_date is None:
        return {
            "period_label": "데이터 없음",
            "promo_cost": 0.0,
            "revenue_before": 0.0,
            "revenue_during": 0.0,
            "revenue_after": 0.0,
            "incremental_revenue": 0.0,
            "roi_rate": 0.0,
            "contributing_factors": [],
        }

    baseline_start = latest_date - timedelta(days=13)
    comparison_start = latest_date - timedelta(days=6)

    query = select(PosDailySalesSnapshot).where(PosDailySalesSnapshot.sales_date >= baseline_start)
    if store_id:
        query = query.where(PosDailySalesSnapshot.store_key == store_id)
    rows = list((await db.execute(query)).scalars().all())

    before_rows = [row for row in rows if row.sales_date < comparison_start]
    during_rows = [row for row in rows if row.sales_date >= comparison_start]

    revenue_before = sum(row.total_sales_amount or 0.0 for row in before_rows)
    revenue_during = sum(row.total_sales_amount or 0.0 for row in during_rows)
    promo_cost = sum(row.discount_amount or 0.0 for row in during_rows)
    incremental_revenue = revenue_during - revenue_before
    roi_rate = round((incremental_revenue / promo_cost) * 100, 2) if promo_cost > 0 else 0.0

    before_guest_count = sum(row.guest_count or 0.0 for row in before_rows)
    during_guest_count = sum(row.guest_count or 0.0 for row in during_rows)
    before_receipts = sum(row.receipt_count or 0.0 for row in before_rows)
    during_receipts = sum(row.receipt_count or 0.0 for row in during_rows)

    before_avg_order = round(revenue_before / before_receipts, 2) if before_receipts else 0.0
    during_avg_order = round(revenue_during / during_receipts, 2) if during_receipts else 0.0
    before_cancel_rate = (
        sum(row.refund_amount or 0.0 for row in before_rows) / revenue_before if revenue_before else 0.0
    )
    during_cancel_rate = (
        sum(row.refund_amount or 0.0 for row in during_rows) / revenue_during if revenue_during else 0.0
    )

    contributing_factors = [
        {
            "factor": "객수 증가",
            "weight": round(((during_guest_count - before_guest_count) / max(before_guest_count, 1.0)) * 100, 2),
        },
        {
            "factor": "객단가 변화",
            "weight": round(((during_avg_order - before_avg_order) / max(before_avg_order, 1.0)) * 100, 2),
        },
        {
            "factor": "취소율 개선",
            "weight": round((before_cancel_rate - during_cancel_rate) * 100, 2),
        },
    ]

    return {
        "period_label": f"{comparison_start.isoformat()} ~ {latest_date.isoformat()}",
        "promo_cost": round(promo_cost, 2),
        "revenue_before": round(revenue_before, 2),
        "revenue_during": round(revenue_during, 2),
        "revenue_after": round(revenue_during, 2),
        "incremental_revenue": round(incremental_revenue, 2),
        "roi_rate": roi_rate,
        "contributing_factors": contributing_factors,
    }


@router.get("/benchmark/stores")
async def benchmark_stores(
    store_id: Optional[str] = Query(None),
    region: Optional[str] = Query(None),
    current_user: User = Depends(require_roles(["hq_admin", "supervisor"])),
    db: AsyncSession = Depends(get_db),
):
    metrics_service = ResourceMetricsService(db)
    latest_date = await metrics_service.get_latest_sales_date()

    pos_rows: list = []
    if latest_date:
        pos_rows = list(
            (
                await db.execute(
                    select(PosDailySalesSnapshot).where(PosDailySalesSnapshot.sales_date == latest_date)
                )
            ).scalars().all()
        )
    if region:
        pos_rows = [row for row in pos_rows if region.lower() in (row.store_name or "").lower() or region.lower() in row.store_key.lower()]

    pos_store_keys = {row.store_key for row in pos_rows}
    target_row = next((row for row in pos_rows if row.store_key == store_id), None) if store_id else None

    result: list[dict[str, Any]] = []
    for row in pos_rows:
        sales_total = round(row.total_sales_amount or 0.0, 2)
        margin_rate = round(
            ((row.net_sales_amount or row.total_sales_amount or 0.0) / max(row.total_sales_amount or 1.0, 1.0)) * 100,
            2,
        ) if sales_total > 0 else 0.0
        review_score = round(max(1.0, 5.0 - (((row.refund_amount or 0.0) / max(sales_total, 1.0)) * 20)), 2)
        if target_row:
            revenue_gap = abs((row.total_sales_amount or 0.0) - (target_row.total_sales_amount or 0.0))
            similarity_score = max(0.0, round(100 - ((revenue_gap / max(target_row.total_sales_amount or 1.0, 1.0)) * 100), 2))
        else:
            similarity_score = 100.0
        result.append(
            {
                "store_id": row.store_key,
                "store_name": row.store_name,
                "region": row.store_key,
                "data_source": "pos",
                "similarity_score": similarity_score,
                "sales_total": sales_total,
                "margin_rate": margin_rate,
                "review_score": review_score,
            }
        )

    # POS 없는 매장(도도포인트만 있는 경우)도 벤치마크 목록에 포함
    dodo_only_q = select(
        DodoPointSnapshot.store_key,
        DodoPointSnapshot.store_name,
        func.count(DodoPointSnapshot.id).label("total_events"),
        func.count(func.distinct(DodoPointSnapshot.customer_uuid)).label("unique_customers"),
    ).where(
        DodoPointSnapshot.store_key.notin_(pos_store_keys)
    ).group_by(DodoPointSnapshot.store_key, DodoPointSnapshot.store_name)

    dodo_only_rows = list((await db.execute(dodo_only_q)).all())
    for drow in dodo_only_rows:
        result.append(
            {
                "store_id": drow.store_key,
                "store_name": drow.store_name,
                "region": drow.store_key,
                "data_source": "dodo_point",
                "similarity_score": 0.0,
                "sales_total": None,
                "margin_rate": None,
                "review_score": None,
                "dodo_total_events": drow.total_events,
                "dodo_unique_customers": drow.unique_customers,
            }
        )

    return sorted(result, key=lambda item: (-item["similarity_score"], -(item["sales_total"] or 0.0)))


@router.get("/benchmark/stores/{store_id}/actions")
async def benchmark_store_actions(
    store_id: str,
    current_user: User = Depends(require_roles(["hq_admin", "supervisor"])),
    db: AsyncSession = Depends(get_db),
):
    metrics_service = ResourceMetricsService(db)
    latest_date = await metrics_service.get_latest_sales_date()
    if latest_date is None:
        return {
            "store_id": store_id,
            "store_name": store_id,
            "benchmark_gaps": [],
            "recommended_actions": [],
        }

    rows = list(
        (
            await db.execute(
                select(PosDailySalesSnapshot).where(PosDailySalesSnapshot.sales_date == latest_date)
            )
        ).scalars().all()
    )
    store_row = next((row for row in rows if row.store_key == store_id), None)
    if store_row is None:
        return {
            "store_id": store_id,
            "store_name": store_id,
            "benchmark_gaps": [],
            "recommended_actions": [],
        }

    avg_sales = mean([row.total_sales_amount or 0.0 for row in rows]) if rows else 0.0
    avg_aov = mean([row.receipt_avg_spend or 0.0 for row in rows]) if rows else 0.0
    avg_cancel_rate = mean(
        [((row.refund_amount or 0.0) / max(row.total_sales_amount or 1.0, 1.0)) * 100 for row in rows]
    ) if rows else 0.0

    store_cancel_rate = ((store_row.refund_amount or 0.0) / max(store_row.total_sales_amount or 1.0, 1.0)) * 100
    benchmark_gaps = []
    recommended_actions = []

    if (store_row.total_sales_amount or 0.0) < avg_sales:
        gap = round(avg_sales - (store_row.total_sales_amount or 0.0), 2)
        benchmark_gaps.append({"metric": "sales_total", "gap": gap, "unit": "KRW"})
        recommended_actions.append(
            {
                "title": "비피크 시간대 객수 보강",
                "description": "유사 매장 평균 대비 매출이 낮습니다. 한산 시간대 세트 제안과 재방문 쿠폰을 우선 적용하세요.",
                "priority": "high",
                "expected_impact": f"+{int(gap):,}원 매출 여지",
            }
        )

    if (store_row.receipt_avg_spend or 0.0) < avg_aov:
        gap = round(avg_aov - (store_row.receipt_avg_spend or 0.0), 2)
        benchmark_gaps.append({"metric": "avg_order_value", "gap": gap, "unit": "KRW"})
        recommended_actions.append(
            {
                "title": "객단가 상향 메뉴 믹스 조정",
                "description": "평균 객단가가 낮습니다. 세트 메뉴와 추가 토핑 제안을 POS 기본 추천으로 노출하세요.",
                "priority": "medium",
                "expected_impact": f"+{int(gap):,}원 객단가 개선 여지",
            }
        )

    if store_cancel_rate > avg_cancel_rate:
        gap = round(store_cancel_rate - avg_cancel_rate, 2)
        benchmark_gaps.append({"metric": "cancel_rate", "gap": gap, "unit": "PCT"})
        recommended_actions.append(
            {
                "title": "취소율 원인 점검",
                "description": "환불 비중이 높습니다. 피크 시간대 제조 지연과 품절 메뉴를 먼저 점검하세요.",
                "priority": "high",
                "expected_impact": f"-{gap}%p 취소율 개선 여지",
            }
        )

    return {
        "store_id": store_id,
        "store_name": store_row.store_name,
        "benchmark_gaps": benchmark_gaps,
        "recommended_actions": recommended_actions,
    }
