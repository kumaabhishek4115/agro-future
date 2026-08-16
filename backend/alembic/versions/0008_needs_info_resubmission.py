"""Add review_reason to projects and project_audit_events table.

Revision ID: 0008
Revises: 0007
Create Date: 2026-08-16

TRD §5.2 – Needs-info resolution and resubmission flow.
  - review_reason: reviewer feedback stored on the project row.
  - project_audit_events: append-only audit log for lifecycle transitions.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add reviewer feedback field to projects
    op.add_column(
        "projects",
        sa.Column("review_reason", sa.String(2000), nullable=True),
    )

    # Create audit_event_enum type
    audit_event_enum = postgresql.ENUM(
        "created",
        "submitted",
        "resubmitted",
        "needs_info",
        "approved",
        "rejected",
        "updated",
        name="audit_event_enum",
    )
    audit_event_enum.create(op.get_bind(), checkfirst=True)

    # Create the project_audit_events table
    op.create_table(
        "project_audit_events",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "project_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "actor_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column(
            "event",
            postgresql.ENUM(
                "created",
                "submitted",
                "resubmitted",
                "needs_info",
                "approved",
                "rejected",
                "updated",
                name="audit_event_enum",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("snapshot_json", sa.Text, nullable=True),
        sa.Column(
            "occurred_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index(
        "ix_project_audit_events_project_id",
        "project_audit_events",
        ["project_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_project_audit_events_project_id",
        table_name="project_audit_events",
    )
    op.drop_table("project_audit_events")
    op.execute("DROP TYPE IF EXISTS audit_event_enum")
    op.drop_column("projects", "review_reason")
