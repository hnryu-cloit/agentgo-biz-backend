from __future__ import annotations

from datetime import date, datetime, time
from typing import Optional

from sqlalchemy import Date, DateTime, Float, Integer, JSON, String, Time
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db.database import Base


class ResourceStore(Base):
    __tablename__ = "resource_stores"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    source_kind: Mapped[str] = mapped_column(String, nullable=False)
    store_key: Mapped[str] = mapped_column(String, nullable=False, index=True)
    external_store_code: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    store_name: Mapped[str] = mapped_column(String, nullable=False)
    latest_file_name: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    metadata_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class PosDailySalesSnapshot(Base):
    __tablename__ = "pos_daily_sales_snapshots"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    store_key: Mapped[str] = mapped_column(String, nullable=False, index=True)
    store_code: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    store_name: Mapped[str] = mapped_column(String, nullable=False)
    sales_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    quantity: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    guest_count: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    guest_avg_spend: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    receipt_count: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    receipt_avg_spend: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    gross_sales_amount: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    refund_amount: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    total_sales_amount: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    discount_amount: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    net_sales_amount: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    sales_amount: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    cash_sales_amount: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    card_sales_amount: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    simple_payment_sales_amount: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    giftcard_sales_amount: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    point_sales_amount: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    order_channel_sales_amount: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    source_file_name: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class BoPointUsageSnapshot(Base):
    __tablename__ = "bo_point_usage_snapshots"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    store_key: Mapped[str] = mapped_column(String, nullable=False, index=True)
    store_code: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    store_name: Mapped[str] = mapped_column(String, nullable=False)
    sales_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    weekday_label: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    receipt_count: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    team_count: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    team_avg_spend: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    customer_count: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    gross_sales_amount: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    sales_amount: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    payment_total_amount: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    net_sales_vat_excluded: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    discount_amount: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    service_discount_amount: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    refund_amount: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    other_sales_amount: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    cash_amount: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    credit_card_total_amount: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    credit_card_pos_amount: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    credit_card_external_amount: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    source_file_name: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class ReceiptTransactionSnapshot(Base):
    __tablename__ = "receipt_transaction_snapshots"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    store_key: Mapped[str] = mapped_column(String, nullable=False, index=True)
    store_name: Mapped[str] = mapped_column(String, nullable=False)
    sales_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    sales_time: Mapped[Optional[time]] = mapped_column(Time, nullable=True)
    pos_name: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    transaction_number: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    sales_category: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    transaction_type: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    cashier_code: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    gross_amount: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    total_quantity: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    discount_amount: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    payment_amount: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    order_number: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    section_code: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    table_name: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    table_staff: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    e_receipt_issued: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    source_file_name: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class MenuLineupSnapshot(Base):
    __tablename__ = "menu_lineup_snapshots"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    store_key: Mapped[str] = mapped_column(String, nullable=False, index=True)
    sheet_name: Mapped[str] = mapped_column(String, nullable=False)
    row_number: Mapped[int] = mapped_column(Integer, nullable=False)
    menu_category: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    menu_name: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    sales_price: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    cost_amount: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    cost_rate: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    row_payload: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    source_file_name: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class DodoPointSnapshot(Base):
    __tablename__ = "dodo_point_snapshots"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    store_key: Mapped[str] = mapped_column(String, nullable=False, index=True)
    store_name: Mapped[str] = mapped_column(String, nullable=False)
    event_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, index=True)
    event_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    customer_masked: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    customer_uuid: Mapped[Optional[str]] = mapped_column(String, nullable=True, index=True)
    point_type: Mapped[str] = mapped_column(String, nullable=False)
    point_amount: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    source_file_name: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
