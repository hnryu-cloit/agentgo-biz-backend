from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional, List

class EmployeeScheduleBase(BaseModel):
    employee_name: str
    role: str
    start_time: datetime
    end_time: datetime
    status: str
    store_id: int

class EmployeeScheduleCreate(EmployeeScheduleBase):
    pass

class EmployeeSchedule(EmployeeScheduleBase):
    model_config = ConfigDict(from_attributes=True)

    id: int

class LaborTargetBase(BaseModel):
    store_id: int
    sales_per_labor_hour_target: float

class LaborTargetCreate(LaborTargetBase):
    pass

class LaborTarget(LaborTargetBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    updated_at: datetime

class LaborPerformance(BaseModel):
    store_id: int
    hour: int
    sales_per_labor_hour: float
    recommended_staff: int
    attainment_rate: float
