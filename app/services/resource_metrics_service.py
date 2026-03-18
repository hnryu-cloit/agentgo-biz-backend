from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta
from typing import Any, List, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.resource_data import (
    DodoPointSnapshot,
    PosDailySalesSnapshot,
    ReceiptTransactionSnapshot,
    ResourceStore,
)


class ResourceMetricsService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_latest_sales_date(self, store_key: Optional[str] = None) -> Optional[date]:
        query = select(func.max(PosDailySalesSnapshot.sales_date))
        if store_key:
            query = query.where(PosDailySalesSnapshot.store_key == store_key)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_previous_sales_date(self, latest_date: date, store_key: Optional[str] = None) -> Optional[date]:
        query = select(func.max(PosDailySalesSnapshot.sales_date)).where(PosDailySalesSnapshot.sales_date < latest_date)
        if store_key:
            query = query.where(PosDailySalesSnapshot.store_key == store_key)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_store_options(self) -> list[dict[str, Any]]:
        result = await self.db.execute(
            select(ResourceStore.store_key, ResourceStore.store_name).where(ResourceStore.store_name.like("%크리스탈제이드%"))
            .where(ResourceStore.source_kind == "pos_daily_sales")
            .order_by(ResourceStore.store_name.asc())
        )
        return [
            {"store_key": row[0], "store_name": row[1]}
            for row in result.fetchall()
        ]

    async def get_owner_dashboard_metrics(self, store_key: Optional[str] = None) -> dict[str, Any]:
        latest_date = await self.get_latest_sales_date(store_key=store_key)
        if latest_date is None:
            return {
                "store_key": store_key,
                "store_name": store_key or "Unknown Store",
                "latest_date": None,
                "today_revenue": 0.0,
                "revenue_vs_yesterday": 0.0,
                "transaction_count": 0,
                "avg_order_value": 0.0,
                "cancel_rate": 0.0,
                "peak_hour": None,
                "kpi_trend": [],
            }

        latest_query = select(PosDailySalesSnapshot).where(PosDailySalesSnapshot.sales_date == latest_date)
        if store_key:
            latest_query = latest_query.where(PosDailySalesSnapshot.store_key == store_key)
        latest_rows = list((await self.db.execute(latest_query.order_by(PosDailySalesSnapshot.store_name.asc()))).scalars().all())

        previous_date = await self.get_previous_sales_date(latest_date, store_key=store_key)
        previous_query = select(PosDailySalesSnapshot).where(PosDailySalesSnapshot.sales_date == previous_date) if previous_date else None
        if previous_query is not None and store_key:
            previous_query = previous_query.where(PosDailySalesSnapshot.store_key == store_key)
        previous_rows = list((await self.db.execute(previous_query)).scalars().all()) if previous_query is not None else []

        today_revenue = sum(row.total_sales_amount or 0.0 for row in latest_rows)
        yesterday_revenue = sum(row.total_sales_amount or 0.0 for row in previous_rows)
        transaction_count = int(sum(row.receipt_count or 0.0 for row in latest_rows))
        guest_count = sum(row.guest_count or 0.0 for row in latest_rows)
        avg_order_value = round(today_revenue / transaction_count, 2) if transaction_count > 0 else 0.0
        cancel_rate = round(
            sum((row.refund_amount or 0.0) for row in latest_rows) / today_revenue,
            4,
        ) if today_revenue > 0 else 0.0

        trend_rows = sorted(latest_rows, key=lambda row: row.store_name)
        kpi_trend = [
            {"label": row.store_name, "revenue": round(row.total_sales_amount or 0.0, 2)}
            for row in trend_rows
        ]
        peak_row = max(trend_rows, key=lambda row: row.total_sales_amount or 0.0, default=None)

        return {
            "store_key": store_key or (latest_rows[0].store_key if latest_rows else None),
            "store_name": peak_row.store_name if store_key is None and peak_row else (latest_rows[0].store_name if latest_rows else store_key or "Unknown Store"),
            "latest_date": latest_date.isoformat(),
            "today_revenue": round(today_revenue, 2),
            "revenue_vs_yesterday": round(today_revenue - yesterday_revenue, 2),
            "transaction_count": transaction_count,
            "avg_order_value": avg_order_value,
            "cancel_rate": cancel_rate,
            "peak_hour": peak_row.store_name if peak_row else None,
            "kpi_trend": kpi_trend,
        }

    async def get_supervisor_summary(self) -> dict[str, Any]:
        latest_date = await self.get_latest_sales_date()
        if latest_date is None:
            return {
                "total_stores": 0,
                "p0_alert_count": 0,
                "avg_cancel_rate": 0.0,
                "low_margin_store_count": 0,
            }

        rows = list(
            (
                await self.db.execute(
                    select(PosDailySalesSnapshot).where(PosDailySalesSnapshot.sales_date == latest_date)
                )
            ).scalars().all()
        )
        avg_cancel_rate = round(
            sum((row.refund_amount or 0.0) for row in rows) / max(sum((row.total_sales_amount or 0.0) for row in rows), 1.0),
            4,
        )
        low_margin_store_count = sum(1 for row in rows if (row.discount_amount or 0.0) > ((row.total_sales_amount or 0.0) * 0.03))
        return {
            "total_stores": len(rows),
            "p0_alert_count": 0,
            "avg_cancel_rate": avg_cancel_rate,
            "low_margin_store_count": low_margin_store_count,
        }

    async def get_supervisor_store_rows(self, store_keys: Optional[List[str]] = None) -> list[dict[str, Any]]:
        latest_date = await self.get_latest_sales_date()
        previous_date = await self.get_previous_sales_date(latest_date) if latest_date else None

        pos_rows: list = []
        previous_rows: list = []

        if latest_date:
            latest_q = select(PosDailySalesSnapshot).where(PosDailySalesSnapshot.sales_date == latest_date)
            prev_q = select(PosDailySalesSnapshot).where(PosDailySalesSnapshot.sales_date == previous_date) if previous_date else None
            if store_keys:
                latest_q = latest_q.where(PosDailySalesSnapshot.store_key.in_(store_keys))
                if prev_q is not None:
                    prev_q = prev_q.where(PosDailySalesSnapshot.store_key.in_(store_keys))
            pos_rows = list((await self.db.execute(latest_q)).scalars().all())
            previous_rows = list((await self.db.execute(prev_q)).scalars().all()) if prev_q is not None else []

        previous_by_key = {row.store_key: row for row in previous_rows}
        pos_store_keys = {row.store_key for row in pos_rows}

        result = []
        for row in pos_rows:
            previous = previous_by_key.get(row.store_key)
            previous_sales = previous.total_sales_amount if previous else 0.0
            sales_delta_pct = round(
                (((row.total_sales_amount or 0.0) - (previous_sales or 0.0)) / previous_sales) * 100,
                2,
            ) if previous_sales else 0.0
            result.append(
                {
                    "id": row.store_key,
                    "name": row.store_name,
                    "region": row.store_key,
                    "size": None,
                    "is_active": True,
                    "data_source": "pos",
                    "alert_count": 0,
                    "risk_score": abs(sales_delta_pct),
                    "sales_total": round(row.total_sales_amount or 0.0, 2),
                    "sales_delta_pct": sales_delta_pct,
                    "avg_order_value": round(row.receipt_avg_spend or 0.0, 2),
                    "cancel_rate": round(((row.refund_amount or 0.0) / max(row.total_sales_amount or 1.0, 1.0)) * 100, 2),
                }
            )

        # POS 데이터가 없는 매장은 도도포인트로 보완
        dodo_stores_q = select(
            DodoPointSnapshot.store_key,
            DodoPointSnapshot.store_name,
            func.max(DodoPointSnapshot.event_date).label("latest_date"),
            func.count(DodoPointSnapshot.id).label("total_events"),
            func.count(func.distinct(DodoPointSnapshot.customer_uuid)).label("unique_customers"),
        ).where(
            DodoPointSnapshot.store_key.notin_(pos_store_keys)
        ).group_by(DodoPointSnapshot.store_key, DodoPointSnapshot.store_name)

        if store_keys:
            dodo_stores_q = dodo_stores_q.where(DodoPointSnapshot.store_key.in_(store_keys))

        dodo_rows = list((await self.db.execute(dodo_stores_q)).all())
        for drow in dodo_rows:
            result.append(
                {
                    "id": drow.store_key,
                    "name": drow.store_name,
                    "region": drow.store_key,
                    "size": None,
                    "is_active": True,
                    "data_source": "dodo_point",
                    "alert_count": 0,
                    "risk_score": 0.0,
                    "sales_total": None,
                    "sales_delta_pct": None,
                    "avg_order_value": None,
                    "cancel_rate": None,
                    "dodo_total_events": drow.total_events,
                    "dodo_unique_customers": drow.unique_customers,
                    "dodo_latest_date": drow.latest_date.isoformat() if drow.latest_date else None,
                }
            )

        return sorted(result, key=lambda item: item["risk_score"], reverse=True)

    async def get_hq_overview(self) -> dict[str, Any]:
        latest_date = await self.get_latest_sales_date()
        previous_date = await self.get_previous_sales_date(latest_date) if latest_date else None
        latest_rows = list(
            (
                await self.db.execute(
                    select(PosDailySalesSnapshot).where(PosDailySalesSnapshot.sales_date == latest_date)
                )
            ).scalars().all()
        ) if latest_date else []
        previous_rows = list(
            (
                await self.db.execute(
                    select(PosDailySalesSnapshot).where(PosDailySalesSnapshot.sales_date == previous_date)
                )
            ).scalars().all()
        ) if previous_date else []
        revenue_total = round(sum(row.total_sales_amount or 0.0 for row in latest_rows), 2)
        previous_total = round(sum(row.total_sales_amount or 0.0 for row in previous_rows), 2)
        return {
            "period_label": latest_date.isoformat() if latest_date else "N/A",
            "total_stores": len(latest_rows),
            "active_alerts": 0,
            "action_compliance_rate": 0.0,
            "revenue_total": revenue_total,
            "revenue_vs_last_week": round(revenue_total - previous_total, 2),
        }

    async def get_receipt_snapshot(self, store_key: str) -> dict[str, Any]:
        latest_date_query = await self.db.execute(
            select(func.max(ReceiptTransactionSnapshot.sales_date)).where(ReceiptTransactionSnapshot.store_key == store_key)
        )
        latest_date = latest_date_query.scalar_one_or_none()
        if latest_date is None:
            return {}

        rows = list(
            (
                await self.db.execute(
                    select(ReceiptTransactionSnapshot)
                    .where(
                        ReceiptTransactionSnapshot.store_key == store_key,
                        ReceiptTransactionSnapshot.sales_date == latest_date,
                    )
                )
            ).scalars().all()
        )
        return {
            "sales_date": latest_date.isoformat(),
            "receipt_count": len(rows),
            "payment_total": round(sum(row.payment_amount or 0.0 for row in rows), 2),
        }

    async def get_dodo_customer_metrics(self, store_key: str, days: int = 90) -> dict[str, Any]:
        """도도포인트 기반 고객 방문 분석 메트릭"""
        latest_date_result = await self.db.execute(
            select(func.max(DodoPointSnapshot.event_date)).where(DodoPointSnapshot.store_key == store_key)
        )
        latest_date = latest_date_result.scalar_one_or_none()
        if latest_date is None:
            return {
                "store_key": store_key,
                "period_days": days,
                "total_events": 0,
                "unique_customers": 0,
                "return_rate": 0.0,
                "earn_count": 0,
                "use_count": 0,
                "daily_trend": [],
                "latest_date": None,
            }

        period_start = latest_date - timedelta(days=days - 1)

        rows = list(
            (
                await self.db.execute(
                    select(DodoPointSnapshot).where(
                        DodoPointSnapshot.store_key == store_key,
                        DodoPointSnapshot.event_date >= period_start,
                        DodoPointSnapshot.event_date <= latest_date,
                    )
                )
            ).scalars().all()
        )

        # 고객별 방문 횟수 집계
        customer_visit_counts: dict[str, int] = defaultdict(int)
        daily_events: dict[date, dict] = defaultdict(lambda: {"visit_count": 0, "unique_uuids": set()})

        earn_count = 0
        use_count = 0

        for row in rows:
            if row.customer_uuid:
                customer_visit_counts[row.customer_uuid] += 1
            if row.point_type == "적립":
                earn_count += 1
            elif row.point_type == "사용":
                use_count += 1
            daily_events[row.event_date]["visit_count"] += 1
            if row.customer_uuid:
                daily_events[row.event_date]["unique_uuids"].add(row.customer_uuid)

        total_customers = len(customer_visit_counts)
        returning_customers = sum(1 for count in customer_visit_counts.values() if count > 1)
        return_rate = round(returning_customers / total_customers, 4) if total_customers > 0 else 0.0

        daily_trend = [
            {
                "date": d.isoformat(),
                "visit_count": data["visit_count"],
                "unique_customers": len(data["unique_uuids"]),
            }
            for d, data in sorted(daily_events.items())
        ]

        # 최근 7일 vs 이전 7일 방문 추세
        recent_7d_start = latest_date - timedelta(days=6)
        prev_7d_start = latest_date - timedelta(days=13)
        recent_visits = sum(e["visit_count"] for d, e in daily_events.items() if d >= recent_7d_start)
        prev_visits = sum(e["visit_count"] for d, e in daily_events.items() if prev_7d_start <= d < recent_7d_start)
        visit_trend_delta = round(
            ((recent_visits - prev_visits) / prev_visits) * 100, 2
        ) if prev_visits > 0 else 0.0

        return {
            "store_key": store_key,
            "period_days": days,
            "latest_date": latest_date.isoformat(),
            "total_events": len(rows),
            "unique_customers": total_customers,
            "return_rate": return_rate,
            "earn_count": earn_count,
            "use_count": use_count,
            "recent_7d_visits": recent_visits,
            "visit_trend_delta_pct": visit_trend_delta,
            "daily_trend": daily_trend,
        }
