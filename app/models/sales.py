from __future__ import annotations
from datetime import datetime, date
from typing import Optional

from sqlalchemy import String, DateTime, Integer, Float, ForeignKey, Date
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db.database import Base


class SalesKpi(Base):
    __tablename__ = "sales_kpis"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    store_id: Mapped[str] = mapped_column(String, ForeignKey("stores.id"), nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    hour: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    revenue: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    transaction_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    avg_order_value: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    cancel_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cancel_rate: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    seat_turnover: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class MenuSales(Base):
    __tablename__ = "menu_sales"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    store_id: Mapped[str] = mapped_column(String, ForeignKey("stores.id"), nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    menu_id: Mapped[str] = mapped_column(String, nullable=False)
    menu_name: Mapped[str] = mapped_column(String, nullable=False)
    category: Mapped[str] = mapped_column(String, nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    revenue: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    cost: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    margin_rate: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    abc_grade: Mapped[Optional[str]] = mapped_column(String, nullable=True)  # A/B/C
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
