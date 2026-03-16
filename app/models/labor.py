from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime
from app.db.database import Base
from datetime import datetime

class EmployeeSchedule(Base):
    __tablename__ = 'employee_schedules'
    id = Column(Integer, primary_key=True, index=True)
    employee_name = Column(String)
    role = Column(String)
    start_time = Column(DateTime)
    end_time = Column(DateTime)
    status = Column(String) # working, waiting, absent, left
    store_id = Column(Integer, ForeignKey('stores.id'))

class LaborTarget(Base):
    __tablename__ = 'labor_targets'
    id = Column(Integer, primary_key=True, index=True)
    store_id = Column(Integer, ForeignKey('stores.id'))
    sales_per_labor_hour_target = Column(Float)
    updated_at = Column(DateTime, default=datetime.utcnow)
