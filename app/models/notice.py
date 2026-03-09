from datetime import datetime
from typing import Optional

from sqlalchemy import String, DateTime, Float, Text, ForeignKey
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db.database import Base


class Notice(Base):
    __tablename__ = "notices"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    file_url: Mapped[str] = mapped_column(String, nullable=False)
    uploaded_by: Mapped[str] = mapped_column(String, ForeignKey("users.id"), nullable=False)
    ocr_status: Mapped[str] = mapped_column(String, nullable=False, default="uploaded")
    # uploaded/preprocessing/extracting/summarizing/completed/failed
    extracted_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    summary: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    checklist: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    ocr_confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    distributed_to: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    distributed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
