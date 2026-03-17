from collections import defaultdict
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import require_roles
from app.db.database import get_db
from app.models.resource_data import DodoPointSnapshot
from app.models.user import User
from app.schemas.labor import EmployeeSchedule, LaborTarget, LaborPerformance, LaborTargetCreate
from app.services.resource_operations_service import ResourceOperationsService

router = APIRouter()

# 시간대별 권장 인원 기준 (방문 건수 → 권장 인원)
_VISIT_TO_STAFF = [
    (0, 1),   # 0~2건 → 1명
    (3, 2),   # 3~7건 → 2명
    (8, 3),   # 8~14건 → 3명
    (15, 4),  # 15건 이상 → 4명
]


def _calc_recommended_staff(visit_count: float) -> int:
    staff = 1
    for threshold, count in _VISIT_TO_STAFF:
        if visit_count >= threshold:
            staff = count
    return staff


@router.get("/hourly-pattern")
async def get_hourly_visit_pattern(
    store_key: str = Query(..., description="매장 키 (예: 크리스탈제이드)"),
    current_user: User = Depends(require_roles(["store_owner", "hq_admin", "supervisor"])),
    db: AsyncSession = Depends(get_db),
):
    """도도포인트 event_at 기반 시간대별 방문 패턴 및 인력 권고"""
    rows = list(
        (
            await db.execute(
                select(DodoPointSnapshot).where(
                    DodoPointSnapshot.store_key == store_key,
                    DodoPointSnapshot.event_at.isnot(None),
                    DodoPointSnapshot.point_type == "적립",  # 방문 proxy = 적립 이벤트
                )
            )
        ).scalars().all()
    )

    if not rows:
        return {
            "store_key": store_key,
            "data_source": "dodo_point",
            "hourly_pattern": [],
            "peak_hours": [],
            "note": "도도포인트 방문 데이터가 없습니다",
        }

    # 시간대별 집계 (0~23시)
    hourly: dict[int, dict] = defaultdict(lambda: {"visit_count": 0, "unique_customers": set()})
    for row in rows:
        hour = row.event_at.hour
        hourly[hour]["visit_count"] += 1
        if row.customer_uuid:
            hourly[hour]["unique_customers"].add(row.customer_uuid)

    total_visits = sum(h["visit_count"] for h in hourly.values())
    avg_hourly = total_visits / max(len(hourly), 1)

    hourly_pattern = []
    for hour in range(24):
        data = hourly.get(hour, {"visit_count": 0, "unique_customers": set()})
        visit_count = data["visit_count"]
        unique = len(data["unique_customers"])
        recommended_staff = _calc_recommended_staff(visit_count)
        hourly_pattern.append(
            {
                "hour": hour,
                "label": f"{hour:02d}:00",
                "visit_count": visit_count,
                "unique_customers": unique,
                "recommended_staff": recommended_staff,
                "is_peak": visit_count > avg_hourly * 1.3,
            }
        )

    peak_hours = [p["hour"] for p in hourly_pattern if p["is_peak"]]

    return {
        "store_key": store_key,
        "data_source": "dodo_point",
        "total_earn_events": len(rows),
        "avg_hourly_visits": round(avg_hourly, 1),
        "peak_hours": peak_hours,
        "hourly_pattern": hourly_pattern,
    }


@router.get('/schedule', response_model=List[EmployeeSchedule])
async def get_schedule(store_id: str = Query(...), date: Optional[str] = None, role: Optional[str] = None):
    service = ResourceOperationsService()
    rows = service.get_labor_schedule(store_id, date)
    if role:
        rows = [row for row in rows if row["role"] == role]
    return [EmployeeSchedule(**row) for row in rows]


@router.get('/productivity', response_model=List[LaborPerformance])
async def get_productivity(store_id: str = Query(...), date: Optional[str] = None):
    service = ResourceOperationsService()
    return [LaborPerformance(**row) for row in service.get_labor_productivity(store_id)]


@router.post('/target', response_model=LaborTarget)
async def set_labor_target(target: LaborTargetCreate):
    return LaborTarget(id=1, updated_at=datetime.now(), **target.model_dump())


@router.get('/available-labor')
async def get_available_labor(store_id: str = Query(...), date: Optional[str] = None):
    service = ResourceOperationsService()
    return service.get_available_labor(store_id, date)
