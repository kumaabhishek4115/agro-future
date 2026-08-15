"""add mobile_number to users

Revision ID: 0005
Revises: 0004
Create Date: 2026-08-15
"""

from alembic import op
import sqlalchemy as sa

revision = "0005"
down_revision = "0004_token_blacklist"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("mobile_number", sa.String(20), nullable=True),
    )
    op.create_index("ix_users_mobile_number", "users", ["mobile_number"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_users_mobile_number", table_name="users")
    op.drop_column("users", "mobile_number")
