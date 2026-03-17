from datetime import datetime
from typing import Optional

from sqlalchemy import String, Boolean, DateTime, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db.database import Base


class Store(Base):
    __tablename__ = "stores"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    region: Mapped[str] = mapped_column(String, nullable=False)
    address: Mapped[str] = mapped_column(String, nullable=False)
    size: Mapped[str] = mapped_column(String, nullable=False)  # 소형/중형/대형
    open_time: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    close_time: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    break_start: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    break_end: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    seats: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    service_type: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    resource_store_key: Mapped[Optional[str]] = mapped_column(String, nullable=True, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class StoreSupervisorAssignment(Base):
    __tablename__ = "store_supervisor_assignments"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    store_id: Mapped[str] = mapped_column(String, ForeignKey("stores.id"), nullable=False)
    supervisor_id: Mapped[str] = mapped_column(String, ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
