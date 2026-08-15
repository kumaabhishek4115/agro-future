"""mobile sms verification: nullable email + otp columns

Revision ID: 0006
Revises: 0005
Create Date: 2026-08-15
"""

from alembic import op
import sqlalchemy as sa

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Accounts may now be created with a mobile number instead of an email.
    op.alter_column("users", "email", existing_type=sa.String(255), nullable=True)
    op.add_column(
        "users", sa.Column("mobile_verification_code", sa.String(255), nullable=True)
    )
    op.add_column(
        "users",
        sa.Column("mobile_code_expires_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "users", sa.Column("mobile_verified_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.create_check_constraint(
        "ck_users_email_or_mobile",
        "users",
        "email IS NOT NULL OR mobile_number IS NOT NULL",
    )


def downgrade() -> None:
    op.drop_constraint("ck_users_email_or_mobile", "users", type_="check")
    op.drop_column("users", "mobile_verified_at")
    op.drop_column("users", "mobile_code_expires_at")
    op.drop_column("users", "mobile_verification_code")
    op.alter_column("users", "email", existing_type=sa.String(255), nullable=False)
