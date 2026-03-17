"""add resource snapshot tables

Revision ID: 20260316_0001
Revises:
Create Date: 2026-03-16 14:30:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20260316_0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "resource_stores",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("source_kind", sa.String(), nullable=False),
        sa.Column("store_key", sa.String(), nullable=False),
        sa.Column("external_store_code", sa.String(), nullable=True),
        sa.Column("store_name", sa.String(), nullable=False),
        sa.Column("latest_file_name", sa.String(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_resource_stores_store_key"), "resource_stores", ["store_key"], unique=False)

    op.create_table(
        "pos_daily_sales_snapshots",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("store_key", sa.String(), nullable=False),
        sa.Column("store_code", sa.String(), nullable=True),
        sa.Column("store_name", sa.String(), nullable=False),
        sa.Column("sales_date", sa.Date(), nullable=False),
        sa.Column("quantity", sa.Float(), nullable=True),
        sa.Column("guest_count", sa.Float(), nullable=True),
        sa.Column("guest_avg_spend", sa.Float(), nullable=True),
        sa.Column("receipt_count", sa.Float(), nullable=True),
        sa.Column("receipt_avg_spend", sa.Float(), nullable=True),
        sa.Column("gross_sales_amount", sa.Float(), nullable=True),
        sa.Column("refund_amount", sa.Float(), nullable=True),
        sa.Column("total_sales_amount", sa.Float(), nullable=True),
        sa.Column("discount_amount", sa.Float(), nullable=True),
        sa.Column("net_sales_amount", sa.Float(), nullable=True),
        sa.Column("sales_amount", sa.Float(), nullable=True),
        sa.Column("cash_sales_amount", sa.Float(), nullable=True),
        sa.Column("card_sales_amount", sa.Float(), nullable=True),
        sa.Column("simple_payment_sales_amount", sa.Float(), nullable=True),
        sa.Column("giftcard_sales_amount", sa.Float(), nullable=True),
        sa.Column("point_sales_amount", sa.Float(), nullable=True),
        sa.Column("order_channel_sales_amount", sa.Float(), nullable=True),
        sa.Column("source_file_name", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_pos_daily_sales_snapshots_sales_date"), "pos_daily_sales_snapshots", ["sales_date"], unique=False)
    op.create_index(op.f("ix_pos_daily_sales_snapshots_store_key"), "pos_daily_sales_snapshots", ["store_key"], unique=False)

    op.create_table(
        "bo_point_usage_snapshots",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("store_key", sa.String(), nullable=False),
        sa.Column("store_code", sa.String(), nullable=True),
        sa.Column("store_name", sa.String(), nullable=False),
        sa.Column("sales_date", sa.Date(), nullable=False),
        sa.Column("weekday_label", sa.String(), nullable=True),
        sa.Column("receipt_count", sa.Float(), nullable=True),
        sa.Column("team_count", sa.Float(), nullable=True),
        sa.Column("team_avg_spend", sa.Float(), nullable=True),
        sa.Column("customer_count", sa.Float(), nullable=True),
        sa.Column("gross_sales_amount", sa.Float(), nullable=True),
        sa.Column("sales_amount", sa.Float(), nullable=True),
        sa.Column("payment_total_amount", sa.Float(), nullable=True),
        sa.Column("net_sales_vat_excluded", sa.Float(), nullable=True),
        sa.Column("discount_amount", sa.Float(), nullable=True),
        sa.Column("service_discount_amount", sa.Float(), nullable=True),
        sa.Column("refund_amount", sa.Float(), nullable=True),
        sa.Column("other_sales_amount", sa.Float(), nullable=True),
        sa.Column("cash_amount", sa.Float(), nullable=True),
        sa.Column("credit_card_total_amount", sa.Float(), nullable=True),
        sa.Column("credit_card_pos_amount", sa.Float(), nullable=True),
        sa.Column("credit_card_external_amount", sa.Float(), nullable=True),
        sa.Column("source_file_name", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_bo_point_usage_snapshots_sales_date"), "bo_point_usage_snapshots", ["sales_date"], unique=False)
    op.create_index(op.f("ix_bo_point_usage_snapshots_store_key"), "bo_point_usage_snapshots", ["store_key"], unique=False)

    op.create_table(
        "receipt_transaction_snapshots",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("store_key", sa.String(), nullable=False),
        sa.Column("store_name", sa.String(), nullable=False),
        sa.Column("sales_date", sa.Date(), nullable=False),
        sa.Column("sales_time", sa.Time(), nullable=True),
        sa.Column("pos_name", sa.String(), nullable=True),
        sa.Column("transaction_number", sa.String(), nullable=True),
        sa.Column("sales_category", sa.String(), nullable=True),
        sa.Column("transaction_type", sa.String(), nullable=True),
        sa.Column("cashier_code", sa.String(), nullable=True),
        sa.Column("gross_amount", sa.Float(), nullable=True),
        sa.Column("total_quantity", sa.Float(), nullable=True),
        sa.Column("discount_amount", sa.Float(), nullable=True),
        sa.Column("payment_amount", sa.Float(), nullable=True),
        sa.Column("order_number", sa.String(), nullable=True),
        sa.Column("section_code", sa.String(), nullable=True),
        sa.Column("table_name", sa.String(), nullable=True),
        sa.Column("table_staff", sa.String(), nullable=True),
        sa.Column("e_receipt_issued", sa.String(), nullable=True),
        sa.Column("source_file_name", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_receipt_transaction_snapshots_sales_date"), "receipt_transaction_snapshots", ["sales_date"], unique=False)
    op.create_index(op.f("ix_receipt_transaction_snapshots_store_key"), "receipt_transaction_snapshots", ["store_key"], unique=False)

    op.create_table(
        "menu_lineup_snapshots",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("store_key", sa.String(), nullable=False),
        sa.Column("sheet_name", sa.String(), nullable=False),
        sa.Column("row_number", sa.Integer(), nullable=False),
        sa.Column("menu_category", sa.String(), nullable=True),
        sa.Column("menu_name", sa.String(), nullable=True),
        sa.Column("sales_price", sa.Float(), nullable=True),
        sa.Column("cost_amount", sa.Float(), nullable=True),
        sa.Column("cost_rate", sa.Float(), nullable=True),
        sa.Column("row_payload", sa.JSON(), nullable=True),
        sa.Column("source_file_name", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_menu_lineup_snapshots_store_key"), "menu_lineup_snapshots", ["store_key"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_menu_lineup_snapshots_store_key"), table_name="menu_lineup_snapshots")
    op.drop_table("menu_lineup_snapshots")

    op.drop_index(op.f("ix_receipt_transaction_snapshots_store_key"), table_name="receipt_transaction_snapshots")
    op.drop_index(op.f("ix_receipt_transaction_snapshots_sales_date"), table_name="receipt_transaction_snapshots")
    op.drop_table("receipt_transaction_snapshots")

    op.drop_index(op.f("ix_bo_point_usage_snapshots_store_key"), table_name="bo_point_usage_snapshots")
    op.drop_index(op.f("ix_bo_point_usage_snapshots_sales_date"), table_name="bo_point_usage_snapshots")
    op.drop_table("bo_point_usage_snapshots")

    op.drop_index(op.f("ix_pos_daily_sales_snapshots_store_key"), table_name="pos_daily_sales_snapshots")
    op.drop_index(op.f("ix_pos_daily_sales_snapshots_sales_date"), table_name="pos_daily_sales_snapshots")
    op.drop_table("pos_daily_sales_snapshots")

    op.drop_index(op.f("ix_resource_stores_store_key"), table_name="resource_stores")
    op.drop_table("resource_stores")
