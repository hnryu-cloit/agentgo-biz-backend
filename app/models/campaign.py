from __future__ import annotations
from datetime import datetime, date
from typing import Optional

from sqlalchemy import String, DateTime, Float, Integer, ForeignKey, Date
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db.database import Base


class Campaign(Base):
    __tablename__ = "campaigns"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    channel: Mapped[str] = mapped_column(String, nullable=False)  # app_push/kakao/email
    target_segment: Mapped[str] = mapped_column(String, nullable=False)
    offer_type: Mapped[str] = mapped_column(String, nullable=False)  # coupon/points/discount
    offer_value: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    message_template: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False, default="draft")  # draft/sent/completed
    sent_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    opened_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    used_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    revisit_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    revenue_attributed: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    created_by: Mapped[str] = mapped_column(String, ForeignKey("users.id"), nullable=False)
    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    start_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    end_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
