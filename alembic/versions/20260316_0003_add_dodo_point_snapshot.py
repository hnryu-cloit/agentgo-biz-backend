"""add dodo point snapshot table

Revision ID: 20260316_0003
Revises: 20260316_0002
Create Date: 2026-03-16 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260316_0003"
down_revision: Union[str, None] = "20260316_0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "dodo_point_snapshots",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("store_key", sa.String(), nullable=False),
        sa.Column("store_name", sa.String(), nullable=False),
        sa.Column("event_at", sa.DateTime(), nullable=True),
        sa.Column("event_date", sa.Date(), nullable=False),
        sa.Column("customer_masked", sa.String(), nullable=True),
        sa.Column("customer_uuid", sa.String(), nullable=True),
        sa.Column("point_type", sa.String(), nullable=False),
        sa.Column("point_amount", sa.Float(), nullable=True),
        sa.Column("source_file_name", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_dodo_point_snapshots_store_key"), "dodo_point_snapshots", ["store_key"], unique=False)
    op.create_index(op.f("ix_dodo_point_snapshots_event_date"), "dodo_point_snapshots", ["event_date"], unique=False)
    op.create_index(op.f("ix_dodo_point_snapshots_event_at"), "dodo_point_snapshots", ["event_at"], unique=False)
    op.create_index(op.f("ix_dodo_point_snapshots_customer_uuid"), "dodo_point_snapshots", ["customer_uuid"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_dodo_point_snapshots_customer_uuid"), table_name="dodo_point_snapshots")
    op.drop_index(op.f("ix_dodo_point_snapshots_event_at"), table_name="dodo_point_snapshots")
    op.drop_index(op.f("ix_dodo_point_snapshots_event_date"), table_name="dodo_point_snapshots")
    op.drop_index(op.f("ix_dodo_point_snapshots_store_key"), table_name="dodo_point_snapshots")
    op.drop_table("dodo_point_snapshots")