from __future__ import annotations
from datetime import datetime, date
from typing import Optional

from sqlalchemy import String, DateTime, ForeignKey, Date
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db.database import Base


class VisitLog(Base):
    __tablename__ = "visit_logs"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    store_id: Mapped[str] = mapped_column(String, ForeignKey("stores.id"), nullable=False)
    supervisor_id: Mapped[str] = mapped_column(String, ForeignKey("users.id"), nullable=False)
    visit_date: Mapped[date] = mapped_column(Date, nullable=False)
    purpose: Mapped[str] = mapped_column(String, nullable=False)
    summary: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    issues_found: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    coaching_points: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    next_visit_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
