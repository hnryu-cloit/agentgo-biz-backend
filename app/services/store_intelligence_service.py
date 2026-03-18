from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from statistics import mean
from typing import Any, Optional

import httpx
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.resource_data import (
    DodoPointSnapshot,
    PosDailySalesSnapshot,
    ReceiptTransactionSnapshot,
)


class StoreIntelligenceService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def build_store_intelligence(self, store_key: Optional[str] = None) -> dict[str, Any]:
        resolved_store_key = store_key or await self._get_default_store_key()
        if not resolved_store_key:
            return {
                "store_id": store_key,
                "summary": "분석 가능한 매장 데이터가 없습니다.",
                "priority_actions": [],
                "sales": None,
                "churn": None,
                "staffing": [],
                "version": None,
            }

        sales_payload, sales_metrics = await self._build_sales_payload(resolved_store_key)
        churn_payload, churn_metrics = await self._build_churn_payload(resolved_store_key)
        staffing_payloads = await self._build_staffing_payloads(resolved_store_key)
        roi_rate = await self._compute_roi_rate(resolved_store_key)

        if not settings.AI_SERVICE_URL:
            raise RuntimeError("AI_SERVICE_URL is not configured")

        payload = {
            "store_id": resolved_store_key,
            "sales_input": sales_payload,
            "churn_input": churn_payload,
            "staffing_inputs": staffing_payloads,
            "roi_rate": roi_rate,
            "avg_order_value": sales_metrics["avg_order_value"],
            "recent_visit_count": churn_metrics["recent_7d_visits"],
        }

        response = await self._post_to_ai("/api/v1/analysis/store-intelligence", payload)
        response["metrics"] = {
            "sales": sales_metrics,
            "churn": churn_metrics,
            "roi_rate": roi_rate,
        }
        return response

    async def _get_default_store_key(self) -> Optional[str]:
        result = await self.db.execute(
            select(PosDailySalesSnapshot.store_key).order_by(PosDailySalesSnapshot.store_name.asc()).limit(1)
        )
        return result.scalar_one_or_none()

    async def _build_sales_payload(self, store_key: str) -> tuple[dict[str, Any], dict[str, Any]]:
        latest_date = (
            await self.db.execute(
                select(func.max(PosDailySalesSnapshot.sales_date)).where(PosDailySalesSnapshot.store_key == store_key)
            )
        ).scalar_one_or_none()
        previous_date = (
            await self.db.execute(
                select(func.max(PosDailySalesSnapshot.sales_date)).where(
                    PosDailySalesSnapshot.store_key == store_key,
                    PosDailySalesSnapshot.sales_date < latest_date,
                )
            )
        ).scalar_one_or_none() if latest_date else None

        latest_row = await self._get_pos_row(store_key, latest_date)
        previous_row = await self._get_pos_row(store_key, previous_date)
        record_count = (
            await self.db.execute(
                select(func.count()).select_from(PosDailySalesSnapshot).where(PosDailySalesSnapshot.store_key == store_key)
            )
        ).scalar_one()
        uploaded_at = (
            await self.db.execute(
                select(func.max(PosDailySalesSnapshot.created_at)).where(PosDailySalesSnapshot.store_key == store_key)
            )
        ).scalar_one_or_none() or datetime.now(timezone.utc)

        latest_revenue = float(latest_row.total_sales_amount or 0.0) if latest_row else 0.0
        previous_revenue = float(previous_row.total_sales_amount or 0.0) if previous_row else 0.0
        latest_guest_count = float(latest_row.guest_count or 0.0) if latest_row else 0.0
        previous_guest_count = float(previous_row.guest_count or 0.0) if previous_row else 0.0
        latest_avg_ticket = float(latest_row.receipt_avg_spend or 0.0) if latest_row else 0.0
        previous_avg_ticket = float(previous_row.receipt_avg_spend or 0.0) if previous_row else 0.0
        latest_channel_mix = self._ratio(
            float(latest_row.order_channel_sales_amount or 0.0) if latest_row else 0.0,
            latest_revenue,
        )
        previous_channel_mix = self._ratio(
            float(previous_row.order_channel_sales_amount or 0.0) if previous_row else 0.0,
            previous_revenue,
        )

        revenue_delta_pct = self._pct_delta(latest_revenue, previous_revenue)
        customer_delta_pct = self._pct_delta(latest_guest_count, previous_guest_count)
        avg_ticket_delta_pct = self._pct_delta(latest_avg_ticket, previous_avg_ticket)
        channel_delta_pct = round((latest_channel_mix - previous_channel_mix) * 100, 2)

        payload = {
            "store_id": store_key,
            "data_window": {
                "start": (previous_date or latest_date or date.today()).isoformat(),
                "end": (latest_date or date.today()).isoformat(),
            },
            "record_count": int(record_count),
            "source_name": "pos_daily_sales_snapshots",
            "uploaded_at": uploaded_at.isoformat(),
            "revenue_delta_pct": revenue_delta_pct,
            "customer_delta_pct": customer_delta_pct,
            "avg_ticket_delta_pct": avg_ticket_delta_pct,
            "channel_delta_pct": channel_delta_pct,
            "weather_impact_pct": 0.0,
        }
        metrics = {
            "latest_date": latest_date.isoformat() if latest_date else None,
            "today_revenue": latest_revenue,
            "previous_revenue": previous_revenue,
            "avg_order_value": latest_avg_ticket,
            "guest_count": latest_guest_count,
            "receipt_count": float(latest_row.receipt_count or 0.0) if latest_row else 0.0,
            "cancel_rate": self._ratio(float(latest_row.refund_amount or 0.0) if latest_row else 0.0, latest_revenue),
        }
        return payload, metrics

    async def _build_churn_payload(self, store_key: str) -> tuple[dict[str, Any], dict[str, Any]]:
        dodo_store_key = self._map_store_to_dodo_key(store_key)
        latest_date = (
            await self.db.execute(
                select(func.max(DodoPointSnapshot.event_date)).where(DodoPointSnapshot.store_key == dodo_store_key)
            )
        ).scalar_one_or_none()
        if latest_date is None:
            now = datetime.now(timezone.utc)
            payload = {
                "store_id": store_key,
                "data_window": {"start": date.today().isoformat(), "end": date.today().isoformat()},
                "record_count": 0,
                "source_name": "dodo_point_snapshots",
                "uploaded_at": now.isoformat(),
                "at_risk_customers": 0,
                "delayed_visit_days": 0.0,
                "avg_visit_cycle_days": 30.0,
                "coupon_redemption_rate": 0.0,
            }
            metrics = {"recent_7d_visits": 0, "return_rate": 0.0, "unique_customers": 0}
            return payload, metrics

        period_start = latest_date - timedelta(days=89)
        rows = list(
            (
                await self.db.execute(
                    select(DodoPointSnapshot).where(
                        DodoPointSnapshot.store_key == dodo_store_key,
                        DodoPointSnapshot.event_date >= period_start,
                        DodoPointSnapshot.event_date <= latest_date,
                    )
                )
            ).scalars().all()
        )
        uploaded_at = max((row.created_at for row in rows), default=datetime.now(timezone.utc))

        visits_by_customer: dict[str, list[date]] = defaultdict(list)
        earn_count = 0
        use_count = 0
        recent_7d_visits = 0
        for row in rows:
            if row.customer_uuid:
                visits_by_customer[row.customer_uuid].append(row.event_date)
            if row.point_type == "적립":
                earn_count += 1
            elif row.point_type == "사용":
                use_count += 1
            if row.event_date >= latest_date - timedelta(days=6):
                recent_7d_visits += 1

        unique_customers = len(visits_by_customer)
        returning_customers = sum(1 for visits in visits_by_customer.values() if len(visits) > 1)
        return_rate = round(returning_customers / unique_customers, 4) if unique_customers else 0.0
        at_risk_last_visits = [
            max(visits)
            for visits in visits_by_customer.values()
            if max(visits) <= latest_date - timedelta(days=30)
        ]
        at_risk_customers = len(at_risk_last_visits)
        delayed_visit_days = round(
            mean((latest_date - last_visit).days for last_visit in at_risk_last_visits),
            2,
        ) if at_risk_last_visits else 0.0
        avg_visits_per_customer = (len(rows) / unique_customers) if unique_customers else 0.0
        avg_visit_cycle_days = round(90 / max(avg_visits_per_customer, 1.0), 2)
        coupon_redemption_rate = round(use_count / max(earn_count, 1), 4)

        payload = {
            "store_id": store_key,
            "data_window": {"start": period_start.isoformat(), "end": latest_date.isoformat()},
            "record_count": len(rows),
            "source_name": "dodo_point_snapshots",
            "uploaded_at": uploaded_at.isoformat(),
            "at_risk_customers": at_risk_customers,
            "delayed_visit_days": delayed_visit_days,
            "avg_visit_cycle_days": max(avg_visit_cycle_days, 1.0),
            "coupon_redemption_rate": coupon_redemption_rate,
        }
        metrics = {
            "recent_7d_visits": recent_7d_visits,
            "return_rate": return_rate,
            "unique_customers": unique_customers,
            "at_risk_customers": at_risk_customers,
        }
        return payload, metrics

    async def _build_staffing_payloads(self, store_key: str) -> list[dict[str, Any]]:
        latest_date = (
            await self.db.execute(
                select(func.max(ReceiptTransactionSnapshot.sales_date)).where(ReceiptTransactionSnapshot.store_key == store_key)
            )
        ).scalar_one_or_none()
        if latest_date is None:
            return []

        rows = list(
            (
                await self.db.execute(
                    select(ReceiptTransactionSnapshot).where(
                        ReceiptTransactionSnapshot.store_key == store_key,
                        ReceiptTransactionSnapshot.sales_date == latest_date,
                    )
                )
            ).scalars().all()
        )
        if not rows:
            return []

        uploaded_at = max((row.created_at for row in rows), default=datetime.now(timezone.utc))
        hourly_sales: dict[int, float] = defaultdict(float)
        hourly_receipts: dict[int, int] = defaultdict(int)
        for row in rows:
            if not row.sales_time:
                continue
            hour = row.sales_time.hour
            hourly_sales[hour] += float(row.payment_amount or 0.0)
            hourly_receipts[hour] += 1

        top_hours = sorted(hourly_sales.keys(), key=lambda hour: hourly_sales[hour], reverse=True)[:3]
        payloads = []
        for hour in top_hours:
            sales = round(hourly_sales[hour], 2)
            staff_actual = max(1, round(hourly_receipts[hour] / 15))
            staff_recommended = max(staff_actual, round(sales / 150000))
            payloads.append(
                {
                    "store_id": store_key,
                    "date": latest_date.isoformat(),
                    "hour": hour,
                    "sales": sales,
                    "staff_actual": int(staff_actual),
                    "staff_recommended": int(staff_recommended),
                    "source_name": "receipt_transaction_snapshots",
                    "uploaded_at": uploaded_at.isoformat(),
                }
            )
        return payloads

    async def _compute_roi_rate(self, store_key: str) -> float:
        latest_date = (
            await self.db.execute(
                select(func.max(PosDailySalesSnapshot.sales_date)).where(PosDailySalesSnapshot.store_key == store_key)
            )
        ).scalar_one_or_none()
        if latest_date is None:
            return 0.0

        baseline_start = latest_date - timedelta(days=13)
        comparison_start = latest_date - timedelta(days=6)
        rows = list(
            (
                await self.db.execute(
                    select(PosDailySalesSnapshot).where(
                        PosDailySalesSnapshot.store_key == store_key,
                        PosDailySalesSnapshot.sales_date >= baseline_start,
                    )
                )
            ).scalars().all()
        )
        before_rows = [row for row in rows if row.sales_date < comparison_start]
        during_rows = [row for row in rows if row.sales_date >= comparison_start]
        revenue_before = sum(float(row.total_sales_amount or 0.0) for row in before_rows)
        revenue_during = sum(float(row.total_sales_amount or 0.0) for row in during_rows)
        promo_cost = sum(float(row.discount_amount or 0.0) for row in during_rows)
        incremental_revenue = revenue_during - revenue_before
        return round((incremental_revenue / promo_cost) * 100, 2) if promo_cost > 0 else 0.0

    async def _get_pos_row(self, store_key: str, sales_date: Optional[date]) -> Optional[PosDailySalesSnapshot]:
        if sales_date is None:
            return None
        result = await self.db.execute(
            select(PosDailySalesSnapshot).where(
                PosDailySalesSnapshot.store_key == store_key,
                PosDailySalesSnapshot.sales_date == sales_date,
            )
        )
        return result.scalar_one_or_none()

    async def _post_to_ai(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        headers = {}
        if settings.AI_SERVICE_TOKEN:
            headers["Authorization"] = f"Bearer {settings.AI_SERVICE_TOKEN}"
        async with httpx.AsyncClient(timeout=settings.AI_SERVICE_TIMEOUT_SECONDS) as client:
            response = await client.post(f"{settings.AI_SERVICE_URL}{path}", json=payload, headers=headers)
            response.raise_for_status()
            return response.json()

    def _map_store_to_dodo_key(self, store_key: str) -> str:
        return "크리스탈제이드" if store_key.startswith("[CJ]") else store_key

    def _pct_delta(self, current: float, previous: float) -> float:
        if previous == 0:
            return 0.0
        return round(((current - previous) / previous) * 100, 2)

    def _ratio(self, numerator: float, denominator: float) -> float:
        if denominator <= 0:
            return 0.0
        return numerator / denominator
