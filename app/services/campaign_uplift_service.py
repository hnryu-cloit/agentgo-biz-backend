from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import httpx
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.resource_data import DodoPointSnapshot, PosDailySalesSnapshot


class CampaignUpliftService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def predict_uplift(
        self,
        *,
        store_key: str,
        segment_name: str,
        channel: str,
        target_customers: int,
        discount_rate: float,
    ) -> dict[str, Any]:
        avg_order_value, recent_visit_count, return_rate, roi_rate, uploaded_at = await self._load_metrics(store_key)
        payload = {
            "store_id": store_key,
            "segment_name": segment_name,
            "channel": channel,
            "target_customers": target_customers,
            "discount_rate": discount_rate,
            "avg_order_value": avg_order_value,
            "recent_visit_count": recent_visit_count,
            "return_rate": return_rate,
            "roi_rate": roi_rate,
            "source_name": "pos_daily_sales_snapshots+dodo_point_snapshots",
            "uploaded_at": uploaded_at.isoformat(),
        }
        return await self._post_to_ai("/api/v1/campaigns/predict-uplift", payload)

    async def _load_metrics(self, store_key: str) -> tuple[float, int, float, float, datetime]:
        latest_sales_date = (
            await self.db.execute(
                select(func.max(PosDailySalesSnapshot.sales_date)).where(PosDailySalesSnapshot.store_key == store_key)
            )
        ).scalar_one_or_none()
        uploaded_at = datetime.now(timezone.utc)
        avg_order_value = 0.0
        roi_rate = 0.0
        if latest_sales_date:
            pos_rows = list(
                (
                    await self.db.execute(
                        select(PosDailySalesSnapshot).where(
                            PosDailySalesSnapshot.store_key == store_key,
                            PosDailySalesSnapshot.sales_date >= latest_sales_date - timedelta(days=13),
                        )
                    )
                ).scalars().all()
            )
            uploaded_at = max((row.created_at for row in pos_rows), default=uploaded_at)
            latest_row = pos_rows[-1] if pos_rows else None
            avg_order_value = float(latest_row.receipt_avg_spend or 0.0) if latest_row else 0.0
            before_rows = pos_rows[:-7] if len(pos_rows) > 7 else pos_rows[: max(len(pos_rows) - 1, 0)]
            during_rows = pos_rows[-7:] if len(pos_rows) >= 7 else pos_rows
            revenue_before = sum(float(row.total_sales_amount or 0.0) for row in before_rows)
            revenue_during = sum(float(row.total_sales_amount or 0.0) for row in during_rows)
            promo_cost = sum(float(row.discount_amount or 0.0) for row in during_rows)
            roi_rate = round(((revenue_during - revenue_before) / promo_cost) * 100, 2) if promo_cost > 0 else 0.0

        dodo_key = "크리스탈제이드" if store_key.startswith("[CJ]") else store_key
        latest_dodo_date = (
            await self.db.execute(
                select(func.max(DodoPointSnapshot.event_date)).where(DodoPointSnapshot.store_key == dodo_key)
            )
        ).scalar_one_or_none()
        if latest_dodo_date is None:
            return avg_order_value, 0, 0.0, roi_rate, uploaded_at
        dodo_rows = list(
            (
                await self.db.execute(
                    select(DodoPointSnapshot).where(
                        DodoPointSnapshot.store_key == dodo_key,
                        DodoPointSnapshot.event_date >= latest_dodo_date - timedelta(days=89),
                        DodoPointSnapshot.event_date <= latest_dodo_date,
                    )
                )
            ).scalars().all()
        )
        uploaded_at = max([uploaded_at, *[row.created_at for row in dodo_rows]], default=uploaded_at)
        recent_visit_count = sum(1 for row in dodo_rows if row.event_date >= latest_dodo_date - timedelta(days=6))
        visits_by_customer: dict[str, int] = {}
        for row in dodo_rows:
            if row.customer_uuid:
                visits_by_customer[row.customer_uuid] = visits_by_customer.get(row.customer_uuid, 0) + 1
        unique_customers = len(visits_by_customer)
        returning_customers = sum(1 for count in visits_by_customer.values() if count > 1)
        return_rate = round(returning_customers / unique_customers, 4) if unique_customers else 0.0
        return avg_order_value, recent_visit_count, return_rate, roi_rate, uploaded_at

    async def _post_to_ai(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        headers = {}
        if settings.AI_SERVICE_TOKEN:
            headers["Authorization"] = f"Bearer {settings.AI_SERVICE_TOKEN}"
        async with httpx.AsyncClient(timeout=settings.AI_SERVICE_TIMEOUT_SECONDS) as client:
            response = await client.post(f"{settings.AI_SERVICE_URL}{path}", json=payload, headers=headers)
            response.raise_for_status()
            return response.json()
