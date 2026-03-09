from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.dependencies import get_current_user, require_roles
from app.db.database import get_db
from app.models.user import User
from app.models.campaign import Campaign
from app.models.store import Store
from app.models.action import Action
from app.services.store_service import StoreService

router = APIRouter()


@router.get("/roi")
async def promo_roi(
    current_user: User = Depends(require_roles(["marketer", "hq_admin"])),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Campaign).where(Campaign.status.in_(["sent", "completed"]))
    )
    campaigns = list(result.scalars().all())

    return [
        {
            "campaign_id": c.id,
            "campaign_name": c.name,
            "channel": c.channel,
            "offer_type": c.offer_type,
            "offer_value": c.offer_value,
            "sent_count": c.sent_count,
            "revenue_before": 0.0,
            "revenue_during": c.revenue_attributed,
            "revenue_after": 0.0,
            "roi_pct": round(
                (c.revenue_attributed - c.offer_value * c.used_count) / max(c.offer_value * c.used_count, 1) * 100,
                2,
            ) if c.used_count > 0 else 0.0,
        }
        for c in campaigns
    ]


@router.get("/benchmark/stores")
async def benchmark_stores(
    current_user: User = Depends(require_roles(["hq_admin", "supervisor"])),
    db: AsyncSession = Depends(get_db),
):
    service = StoreService(db)
    stores = await service.get_stores_for_user(current_user)

    return [
        {
            "store_id": s.id,
            "store_name": s.name,
            "region": s.region,
            "size": s.size,
            "avg_revenue": 0.0,
            "avg_cancel_rate": 0.0,
            "avg_order_value": 0.0,
            "seat_turnover": 0.0,
        }
        for s in stores
    ]


@router.get("/benchmark/stores/{store_id}/actions")
async def benchmark_store_actions(
    store_id: str,
    current_user: User = Depends(require_roles(["hq_admin", "supervisor"])),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Store).where(Store.id == store_id))
    store = result.scalar_one_or_none()

    return {
        "store_id": store_id,
        "store_name": store.name if store else "Unknown",
        "benchmark_gaps": [],
        "recommended_actions": [
            {
                "title": "피크타임 인력 배치 최적화",
                "description": "동일 규모 매장 대비 좌석회전율이 낮습니다.",
                "priority": "P1",
                "expected_impact": "+8% 매출",
            }
        ],
    }
