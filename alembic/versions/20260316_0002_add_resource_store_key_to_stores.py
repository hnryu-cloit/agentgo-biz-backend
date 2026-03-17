"""add resource_store_key to stores

Revision ID: 20260316_0002
Revises: 20260316_0001
Create Date: 2026-03-16 15:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20260316_0002"
down_revision: Union[str, None] = "20260316_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("stores", sa.Column("resource_store_key", sa.String(), nullable=True))
    op.create_index("ix_stores_resource_store_key", "stores", ["resource_store_key"])


def downgrade() -> None:
    op.drop_index("ix_stores_resource_store_key", table_name="stores")
    op.drop_column("stores", "resource_store_key")