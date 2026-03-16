from fastapi import APIRouter, Depends, HTTPException
from typing import List, Any, Optional
from app.schemas.labor import EmployeeSchedule, LaborTarget, LaborPerformance, LaborTargetCreate
from datetime import datetime, timedelta

router = APIRouter()

@router.get('/schedule', response_model=List[EmployeeSchedule])
async def get_schedule(store_id: int, date: Optional[str] = None, role: Optional[str] = None):
    # Mock data for employee schedules
    return [
        EmployeeSchedule(id=1, employee_name='김철수', role='주방', start_time=datetime.now(), end_time=datetime.now() + timedelta(hours=8), status='working', store_id=store_id),
        EmployeeSchedule(id=2, employee_name='이영희', role='홀', start_time=datetime.now(), end_time=datetime.now() + timedelta(hours=4), status='waiting', store_id=store_id)
    ]

@router.get('/productivity', response_model=List[LaborPerformance])
async def get_productivity(store_id: int):
    # Mock hourly sales per labor hour (SPLH) calculation
    return [
        LaborPerformance(store_id=store_id, hour=11, sales_per_labor_hour=45000.0, recommended_staff=3, attainment_rate=0.9),
        LaborPerformance(store_id=store_id, hour=12, sales_per_labor_hour=55000.0, recommended_staff=4, attainment_rate=1.1)
    ]

@router.post('/target', response_model=LaborTarget)
async def set_labor_target(target: LaborTargetCreate):
    # Mock target setting
    return LaborTarget(id=1, updated_at=datetime.now(), **target.model_dump())

@router.get('/available-labor')
async def get_available_labor(store_id: int):
    # 시간대별 가용 인원 집계
    return {'store_id': store_id, 'available_count': 5, 'roles': {'kitchen': 2, 'hall': 3}}
