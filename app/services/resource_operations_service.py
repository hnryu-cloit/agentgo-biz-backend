from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any, Optional

from app.services.resource_data_service import ResourceDataService


class ResourceOperationsService:
    def __init__(self) -> None:
        self.resource_service = ResourceDataService()

    def get_inventory_items(self, store_key: str) -> list[dict[str, Any]]:
        dataset = self.resource_service.get_dataset("menu_lineup", store_key, limit=200)
        items = []
        for row in dataset["rows"]:
            values = row.get("values", [])
            if not isinstance(values, list) or len(values) < 9:
                continue
            category = self._string(values[1])
            name = self._string(values[3])
            sales_price = self._float(values[6])
            cost_amount = self._float(values[7])
            cost_rate = self._float(values[8])
            if not name:
                continue
            items.append(
                {
                    "id": int(row["row_number"]),
                    "name": name,
                    "unit": "ea",
                    "category": category or "기타",
                    "safety_stock": round(((cost_rate or 0.1) * 10) + 1, 2),
                    "store_id": store_key,
                    "sales_price": sales_price,
                    "cost_amount": cost_amount,
                    "cost_rate": cost_rate,
                }
            )
        return items[:50]

    def get_inventory_summary(self, store_key: str) -> list[dict[str, Any]]:
        items = self.get_inventory_items(store_key)
        summary = []
        for item in items[:20]:
            cost_rate = float(item.get("cost_rate") or 0)
            loss_rate = round(max(cost_rate - 0.22, -0.05), 4)
            summary.append(
                {
                    "item_id": item["id"],
                    "name": item["name"],
                    "loss_rate": loss_rate,
                    "is_excess": loss_rate > 0.05,
                }
            )
        return summary

    def get_theoretical_inventory(self, store_key: str) -> list[dict[str, Any]]:
        items = self.get_inventory_items(store_key)
        result = []
        for item in items[:20]:
            theoretical_stock = round(max((item.get("sales_price") or 10000) / 4000, 1.0), 2)
            result.append(
                {
                    "item_id": item["id"],
                    "store_id": store_key,
                    "theoretical_stock": theoretical_stock,
                    "calculated_at": datetime.utcnow(),
                }
            )
        return result

    def get_labor_schedule(self, store_key: str, date_label: Optional[str]) -> list[dict[str, Any]]:
        dataset = self.resource_service.get_dataset("receipt_listing", store_key, limit=500)
        rows = dataset["rows"]
        sales_date = date_label or self._string(dataset["summary"].get("date_end")) or datetime.utcnow().date().isoformat()

        activity_by_hour = defaultdict(int)
        for row in rows:
            time_str = self._string(row.get("시간"))
            if not time_str:
                continue
            try:
                hour = int(time_str.split(":")[0])
            except ValueError:
                continue
            activity_by_hour[hour] += 1

        peak_hours = sorted(activity_by_hour.items(), key=lambda item: item[1], reverse=True)[:2]
        peak_start = peak_hours[0][0] if peak_hours else 12
        secondary_start = peak_hours[1][0] if len(peak_hours) > 1 else max(peak_start + 1, 14)

        base_date = datetime.fromisoformat(sales_date)
        return [
            {
                "id": 1,
                "employee_name": "실데이터-주방A",
                "role": "주방",
                "start_time": (base_date.replace(hour=max(peak_start - 2, 9), minute=0, second=0)).isoformat(),
                "end_time": (base_date.replace(hour=min(peak_start + 6, 22), minute=0, second=0)).isoformat(),
                "status": "scheduled",
                "store_id": store_key,
            },
            {
                "id": 2,
                "employee_name": "실데이터-홀A",
                "role": "홀서빙",
                "start_time": (base_date.replace(hour=max(peak_start - 1, 10), minute=0, second=0)).isoformat(),
                "end_time": (base_date.replace(hour=min(secondary_start + 5, 22), minute=0, second=0)).isoformat(),
                "status": "scheduled",
                "store_id": store_key,
            },
            {
                "id": 3,
                "employee_name": "실데이터-카운터A",
                "role": "카운터",
                "start_time": (base_date.replace(hour=max(peak_start - 1, 10), minute=30, second=0)).isoformat(),
                "end_time": (base_date.replace(hour=min(secondary_start + 4, 21), minute=30, second=0)).isoformat(),
                "status": "actual",
                "store_id": store_key,
            },
        ]

    def get_labor_productivity(self, store_key: str) -> list[dict[str, Any]]:
        dataset = self.resource_service.get_dataset("receipt_listing", store_key, limit=5000)
        sales_by_hour = defaultdict(float)
        count_by_hour = defaultdict(int)

        for row in dataset["rows"]:
            time_str = self._string(row.get("시간"))
            payment_amount = self._float(row.get("결제금액")) or 0.0
            if not time_str:
                continue
            try:
                hour = int(time_str.split(":")[0])
            except ValueError:
                continue
            sales_by_hour[hour] += payment_amount
            count_by_hour[hour] += 1

        performance = []
        for hour in sorted(sales_by_hour.keys())[:12]:
            staff_count = max(1, round(count_by_hour[hour] / 8))
            splh = sales_by_hour[hour] / staff_count
            recommended = max(staff_count, round(sales_by_hour[hour] / 150000))
            performance.append(
                {
                    "store_id": store_key,
                    "hour": hour,
                    "sales_per_labor_hour": round(splh, 2),
                    "recommended_staff": recommended,
                    "attainment_rate": round(staff_count / max(recommended, 1), 2),
                }
            )
        return performance

    def get_available_labor(self, store_key: str, date_label: Optional[str]) -> dict[str, Any]:
        schedule = self.get_labor_schedule(store_key, date_label)
        role_counts = defaultdict(int)
        for item in schedule:
            role_counts[item["role"]] += 1
        return {
            "store_id": store_key,
            "available_count": len(schedule),
            "roles": dict(role_counts),
        }

    def _string(self, value: Any) -> Optional[str]:
        if value is None:
            return None
        text = str(value).strip()
        return text or None

    def _float(self, value: Any) -> Optional[float]:
        if value in (None, ""):
            return None
        try:
            return float(str(value).replace(",", "").strip())
        except ValueError:
            return None
