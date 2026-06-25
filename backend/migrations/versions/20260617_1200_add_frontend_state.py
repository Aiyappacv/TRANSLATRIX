"""add frontend compatibility state

Revision ID: 8e8c5d77c9a1
Revises: e0ee21fd6b03
Create Date: 2026-06-17 12:00:00
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "8e8c5d77c9a1"
down_revision: Union[str, None] = "e0ee21fd6b03"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "frontend_state",
        sa.Column("scope_key", sa.String(length=180), nullable=False),
        sa.Column("namespace", sa.String(length=100), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("scope_key", "namespace"),
    )


def downgrade() -> None:
    op.drop_table("frontend_state")
