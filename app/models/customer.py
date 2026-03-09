from __future__ import annotations
from datetime import datetime, date
from typing import Optional

from sqlalchemy import String, DateTime, Integer, Float, ForeignKey, Date
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db.database import Base


class Customer(Base):
    __tablename__ = "customers"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    store_id: Mapped[str] = mapped_column(String, ForeignKey("stores.id"), nullable=False)
    external_key: Mapped[str] = mapped_column(String, nullable=False)  # PII-masked
    rfm_segment: Mapped[Optional[str]] = mapped_column(String, nullable=True)  # vip/loyal/at_risk/churned
    visit_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_visit_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    avg_order_value: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    total_ltv: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    risk_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    days_since_last_visit: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class RfmSnapshot(Base):
    __tablename__ = "rfm_snapshots"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    store_id: Mapped[str] = mapped_column(String, ForeignKey("stores.id"), nullable=False)
    snapshot_date: Mapped[date] = mapped_column(Date, nullable=False)
    vip_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    loyal_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    at_risk_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    churned_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    vip_sales_share: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    loyal_sales_share: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    at_risk_sales_share: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    churned_sales_share: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
