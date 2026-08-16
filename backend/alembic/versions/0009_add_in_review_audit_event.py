"""Add in_review to audit_event_enum.

Revision ID: 0009
Revises: 0008
Create Date: 2026-08-16

TRD §5.2 – Review workflow status transitions should be auditable, including
the in_review state shown to farmers in their intake timeline.
"""

from __future__ import annotations

from alembic import op

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TYPE audit_event_enum ADD VALUE IF NOT EXISTS 'in_review'")


def downgrade() -> None:
    # PostgreSQL cannot drop individual enum values in place.
    pass
