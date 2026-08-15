"""Add token_blacklist table for server-side JWT invalidation on logout

Revision ID: 0004_token_blacklist
Revises: 0003_supplier_profile_partial_completion
Create Date: 2026-08-15

TRD §8 – session tokens must be invalidated on logout.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision = "0004_token_blacklist"
down_revision = "0003_supplier_profile_partial_completion"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "token_blacklist",
        sa.Column("id", UUID(as_uuid=True), nullable=False),
        sa.Column("token", sa.String(2048), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("blacklisted_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token", name="uq_token_blacklist_token"),
    )
    op.create_index("ix_token_blacklist_token", "token_blacklist", ["token"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_token_blacklist_token", table_name="token_blacklist")
    op.drop_table("token_blacklist")
