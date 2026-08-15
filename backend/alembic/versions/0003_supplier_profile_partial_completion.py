"""Allow partial supplier profile saves

Revision ID: 0003_supplier_profile_partial_completion
Revises: 0002_project_intake
Create Date: 2026-08-15
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0003_supplier_partial"
down_revision = "0002_project_intake"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("supplier_profiles", "geography", existing_type=sa.String(255), nullable=True)
    op.alter_column(
        "supplier_profiles",
        "land_size_hectares",
        existing_type=sa.Float(),
        nullable=True,
    )
    op.alter_column(
        "supplier_profiles",
        "crop_or_livestock_type",
        existing_type=sa.String(255),
        nullable=True,
    )
    op.alter_column(
        "supplier_profiles",
        "ownership_status",
        existing_type=sa.Enum("owned", "leased", "cooperative", name="ownership_status_enum"),
        nullable=True,
    )
    op.alter_column(
        "supplier_profiles",
        "payout_details",
        existing_type=sa.String(1000),
        nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "supplier_profiles",
        "payout_details",
        existing_type=sa.String(1000),
        nullable=False,
    )
    op.alter_column(
        "supplier_profiles",
        "ownership_status",
        existing_type=sa.Enum("owned", "leased", "cooperative", name="ownership_status_enum"),
        nullable=False,
    )
    op.alter_column(
        "supplier_profiles",
        "crop_or_livestock_type",
        existing_type=sa.String(255),
        nullable=False,
    )
    op.alter_column(
        "supplier_profiles",
        "land_size_hectares",
        existing_type=sa.Float(),
        nullable=False,
    )
    op.alter_column("supplier_profiles", "geography", existing_type=sa.String(255), nullable=False)
