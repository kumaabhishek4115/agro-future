"""Audit trail enhancements for P0 compliance requirements.

Revision ID: 0010
Revises: 0009
Create Date: 2026-08-16

Adds the following to project_audit_events:
  - actor_role   : role of the actor at event time
  - resource_type: type of the primary resource (project, document, …)
  - resource_id  : UUID of the primary resource
  - reason       : optional reason or metadata text

Also adds three new audit event types:
  - document_uploaded : a supporting document was attached or replaced
  - offer_accepted    : farmer accepted a buyer offer
  - offer_rejected    : farmer rejected a buyer offer

TRD §5.2 – Review workflow audit requirements
TRD §8   – Security and audit
TRD §10  – Compliance and data retention
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add new enum values to audit_event_enum
    op.execute("ALTER TYPE audit_event_enum ADD VALUE IF NOT EXISTS 'document_uploaded'")
    op.execute("ALTER TYPE audit_event_enum ADD VALUE IF NOT EXISTS 'offer_accepted'")
    op.execute("ALTER TYPE audit_event_enum ADD VALUE IF NOT EXISTS 'offer_rejected'")

    # Add new columns to project_audit_events
    op.add_column(
        "project_audit_events",
        sa.Column("actor_role", sa.String(50), nullable=True),
    )
    op.add_column(
        "project_audit_events",
        sa.Column("resource_type", sa.String(50), nullable=True),
    )
    op.add_column(
        "project_audit_events",
        sa.Column(
            "resource_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
    )
    op.add_column(
        "project_audit_events",
        sa.Column("reason", sa.Text, nullable=True),
    )


def downgrade() -> None:
    op.drop_column("project_audit_events", "reason")
    op.drop_column("project_audit_events", "resource_id")
    op.drop_column("project_audit_events", "resource_type")
    op.drop_column("project_audit_events", "actor_role")
    # PostgreSQL cannot drop individual enum values in place.
