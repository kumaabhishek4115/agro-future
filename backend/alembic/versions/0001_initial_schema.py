"""Initial schema: users and supplier_profiles tables (Epic 1 – Farmer Onboarding)

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-08-15

TRD §6 – Minimum entities implemented here:
  - users            (id, role, org_id, status, email, password_hash, …)
  - supplier_profiles (user_id FK → users.id, farm metadata, payout metadata)

Enumerations:
  - role_enum:             supplier | buyer | operator | admin
  - user_status_enum:      pending_verification | active | suspended
  - ownership_status_enum: owned | leased | cooperative
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# ---------------------------------------------------------------------------
# Revision identifiers
# ---------------------------------------------------------------------------
revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _create_enum(name: str, *values: str) -> postgresql.ENUM:
    """Return a server-side PostgreSQL ENUM type."""
    return postgresql.ENUM(*values, name=name, create_type=False)


# ---------------------------------------------------------------------------
# upgrade
# ---------------------------------------------------------------------------

def upgrade() -> None:
    # ------------------------------------------------------------------
    # Create ENUM types (must exist before the columns that use them)
    # ------------------------------------------------------------------
    role_enum = postgresql.ENUM(
        "supplier", "buyer", "operator", "admin",
        name="role_enum",
    )
    role_enum.create(op.get_bind(), checkfirst=True)

    user_status_enum = postgresql.ENUM(
        "pending_verification", "active", "suspended",
        name="user_status_enum",
    )
    user_status_enum.create(op.get_bind(), checkfirst=True)

    ownership_status_enum = postgresql.ENUM(
        "owned", "leased", "cooperative",
        name="ownership_status_enum",
    )
    ownership_status_enum.create(op.get_bind(), checkfirst=True)

    # ------------------------------------------------------------------
    # Table: users
    #
    # Central identity record.  Stores credentials, role, and verification
    # state.  All other entities are linked back to this table.
    # TRD §4, §5.1, §6.
    # ------------------------------------------------------------------
    op.create_table(
        "users",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column(
            "role",
            _create_enum("role_enum", "supplier", "buyer", "operator", "admin"),
            nullable=False,
            server_default="supplier",
        ),
        # org_id: optional link to a farmer cooperative / organisation record
        sa.Column("org_id", sa.String(100), nullable=True),
        sa.Column(
            "status",
            _create_enum(
                "user_status_enum",
                "pending_verification", "active", "suspended",
            ),
            nullable=False,
            server_default="pending_verification",
        ),
        # One-time token sent in the verification email (TRD §5.1)
        sa.Column("email_verification_token", sa.String(255), nullable=True),
        sa.Column(
            "email_verified_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
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

    # Unique email constraint (enforce at DB level)
    op.create_index("uq_users_email", "users", ["email"], unique=True)

    # ------------------------------------------------------------------
    # Table: supplier_profiles
    #
    # One-to-one with users (one profile per supplier account).
    # Captures farm geography, land size, crop/livestock type,
    # ownership / lease status, and payout details.
    # TRD §5.1, §6.
    # ------------------------------------------------------------------
    op.create_table(
        "supplier_profiles",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        # -- Farm metadata --
        sa.Column("geography", sa.String(255), nullable=False),
        sa.Column("land_size_hectares", sa.Float, nullable=False),
        sa.Column("crop_or_livestock_type", sa.String(255), nullable=False),
        sa.Column(
            "ownership_status",
            _create_enum(
                "ownership_status_enum",
                "owned", "leased", "cooperative",
            ),
            nullable=False,
        ),
        # -- Payout metadata --
        # Stored as plain text for MVP; encrypt at rest in production (TRD §8)
        sa.Column("payout_details", sa.String(1000), nullable=False),
        # True once all required profile fields have been saved (TRD §5.1 validation)
        sa.Column(
            "is_complete",
            sa.Boolean,
            nullable=False,
            server_default=sa.text("false"),
        ),
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

    # One profile per user (one-to-one enforcement at DB level)
    op.create_index(
        "uq_supplier_profiles_user_id",
        "supplier_profiles",
        ["user_id"],
        unique=True,
    )
    # Fast lookup by user_id
    op.create_index(
        "ix_supplier_profiles_user_id",
        "supplier_profiles",
        ["user_id"],
    )


# ---------------------------------------------------------------------------
# downgrade
# ---------------------------------------------------------------------------

def downgrade() -> None:
    # Drop tables in reverse dependency order
    op.drop_index("ix_supplier_profiles_user_id", table_name="supplier_profiles")
    op.drop_index("uq_supplier_profiles_user_id", table_name="supplier_profiles")
    op.drop_table("supplier_profiles")

    op.drop_index("uq_users_email", table_name="users")
    op.drop_table("users")

    # Drop ENUM types after the tables are gone
    op.execute("DROP TYPE IF EXISTS ownership_status_enum")
    op.execute("DROP TYPE IF EXISTS user_status_enum")
    op.execute("DROP TYPE IF EXISTS role_enum")
