"""Add baseline and expected_volume to projects table.

Revision ID: 0007
Revises: 0006_mobile_sms_verification
Create Date: 2026-08-15
"""

from alembic import op
import sqlalchemy as sa

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("projects", sa.Column("baseline", sa.String(2000), nullable=True))
    op.add_column("projects", sa.Column("expected_volume", sa.Float, nullable=True))


def downgrade() -> None:
    op.drop_column("projects", "expected_volume")
    op.drop_column("projects", "baseline")
