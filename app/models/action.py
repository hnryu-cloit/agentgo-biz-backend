from __future__ import annotations
from datetime import datetime, date
from typing import Optional

from sqlalchemy import String, DateTime, ForeignKey, Date
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db.database import Base


class Action(Base):
    __tablename__ = "actions"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    store_id: Mapped[str] = mapped_column(String, ForeignKey("stores.id"), nullable=False)
    created_by: Mapped[str] = mapped_column(String, ForeignKey("users.id"), nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(String, nullable=False)
    category: Mapped[str] = mapped_column(String, nullable=False)
    priority: Mapped[str] = mapped_column(String, nullable=False)  # P0/P1/P2
    status: Mapped[str] = mapped_column(String, nullable=False, default="pending")  # pending/executed/deferred/ignored
    defer_reason: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    ai_basis: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    expected_impact: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    due_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    executed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
