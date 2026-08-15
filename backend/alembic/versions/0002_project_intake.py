"""Epic 2 – Project Intake: projects and project_documents tables

Revision ID: 0002_project_intake
Revises: 0001_initial_schema
Create Date: 2026-08-15

TRD §5.1 – Project submission form with draft + submitted states;
            document upload support.
TRD §5.2 – Review queue statuses (in_review, needs_info, approved, rejected).
TRD §6   – projects (supplier_id, methodology, geography, status);
            project_documents (project_id, type, storage_uri, checksum).

New ENUM types:
  - project_status_enum:  draft | submitted | in_review | needs_info | approved | rejected
  - document_type_enum:   registry_evidence | mrv_record | land_ownership_proof | other
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# ---------------------------------------------------------------------------
# Revision identifiers
# ---------------------------------------------------------------------------
revision = "0002_project_intake"
down_revision = "0001_initial_schema"
branch_labels = None
depends_on = None


# ---------------------------------------------------------------------------
# upgrade
# ---------------------------------------------------------------------------

def upgrade() -> None:
    # ------------------------------------------------------------------
    # Create ENUM types
    # ------------------------------------------------------------------
    project_status_enum = postgresql.ENUM(
        "draft", "submitted", "in_review", "needs_info", "approved", "rejected",
        name="project_status_enum",
    )
    project_status_enum.create(op.get_bind(), checkfirst=True)

    document_type_enum = postgresql.ENUM(
        "registry_evidence", "mrv_record", "land_ownership_proof", "other",
        name="document_type_enum",
    )
    document_type_enum.create(op.get_bind(), checkfirst=True)

    # ------------------------------------------------------------------
    # Table: projects
    #
    # One supplier (user) can have many projects.
    # TRD §5.1, §5.2, §6.
    # ------------------------------------------------------------------
    op.create_table(
        "projects",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "supplier_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.String(2000), nullable=True),
        sa.Column("methodology", sa.String(255), nullable=False),
        sa.Column("geography", sa.String(255), nullable=False),
        sa.Column(
            "status",
            postgresql.ENUM(
                "draft", "submitted", "in_review", "needs_info", "approved", "rejected",
                name="project_status_enum",
                create_type=False,
            ),
            nullable=False,
            server_default="draft",
        ),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    op.create_index("ix_projects_supplier_id", "projects", ["supplier_id"])

    # ------------------------------------------------------------------
    # Table: project_documents
    #
    # Each row is one uploaded document attached to a project.
    # TRD §5.1, §6.
    # ------------------------------------------------------------------
    op.create_table(
        "project_documents",
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
            "doc_type",
            postgresql.ENUM(
                "registry_evidence", "mrv_record", "land_ownership_proof", "other",
                name="document_type_enum",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("storage_uri", sa.String(1000), nullable=False),
        # SHA-256 hex digest for integrity verification
        sa.Column("checksum", sa.String(64), nullable=False),
        sa.Column(
            "uploaded_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    op.create_index("ix_project_documents_project_id", "project_documents", ["project_id"])


# ---------------------------------------------------------------------------
# downgrade
# ---------------------------------------------------------------------------

def downgrade() -> None:
    op.drop_index("ix_project_documents_project_id", table_name="project_documents")
    op.drop_table("project_documents")

    op.drop_index("ix_projects_supplier_id", table_name="projects")
    op.drop_table("projects")

    op.execute("DROP TYPE IF EXISTS document_type_enum")
    op.execute("DROP TYPE IF EXISTS project_status_enum")
