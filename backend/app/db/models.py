"""
SQLAlchemy ORM models for Epic 1: Farmer Account Onboarding.

Entities modelled here mirror TRD §6:
  - users            (id, role, org_id, status)
  - supplier_profiles (user_id, farm metadata, payout metadata)

Relationships
─────────────
User ──< SupplierProfile   (one-to-one; a supplier has exactly one profile)
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


# ---------------------------------------------------------------------------
# Enumerations stored as native PostgreSQL ENUM types
# ---------------------------------------------------------------------------

import enum as _enum


class RoleEnum(str, _enum.Enum):
    supplier = "supplier"
    buyer = "buyer"
    operator = "operator"
    admin = "admin"


class UserStatusEnum(str, _enum.Enum):
    pending_verification = "pending_verification"
    active = "active"
    suspended = "suspended"


class OwnershipStatusEnum(str, _enum.Enum):
    owned = "owned"
    leased = "leased"
    cooperative = "cooperative"


# ---------------------------------------------------------------------------
# users
# ---------------------------------------------------------------------------

class User(Base):
    """
    Central identity record.

    TRD §4  – role-based access control.
    TRD §5.1 – supplier account registration with email verification.
    TRD §6   – users (id, role, org_id, status).
    """

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[RoleEnum] = mapped_column(
        Enum(RoleEnum, name="role_enum"), nullable=False, default=RoleEnum.supplier
    )
    # org_id is nullable for individual farmers not belonging to a cooperative org
    org_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    status: Mapped[UserStatusEnum] = mapped_column(
        Enum(UserStatusEnum, name="user_status_enum"),
        nullable=False,
        default=UserStatusEnum.pending_verification,
    )
    email_verification_token: Mapped[str | None] = mapped_column(String(255), nullable=True)
    email_verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_now, onupdate=_now
    )

    # Relationships
    supplier_profile: Mapped[SupplierProfile | None] = relationship(
        "SupplierProfile", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<User id={self.id} email={self.email} role={self.role}>"


# ---------------------------------------------------------------------------
# supplier_profiles
# ---------------------------------------------------------------------------

class SupplierProfile(Base):
    """
    Farm metadata and payout details captured during supplier onboarding.

    TRD §5.1 – Profile fields: geography, land size, crop/livestock type,
                ownership/lease status, payout details.
    TRD §6   – supplier_profiles (user_id, farm metadata, payout metadata).
    """

    __tablename__ = "supplier_profiles"
    __table_args__ = (
        UniqueConstraint("user_id", name="uq_supplier_profiles_user_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Farm metadata (TRD §5.1)
    geography: Mapped[str] = mapped_column(String(255), nullable=False)
    land_size_hectares: Mapped[float] = mapped_column(Float, nullable=False)
    crop_or_livestock_type: Mapped[str] = mapped_column(String(255), nullable=False)
    ownership_status: Mapped[OwnershipStatusEnum] = mapped_column(
        Enum(OwnershipStatusEnum, name="ownership_status_enum"), nullable=False
    )

    # Payout metadata – stored as an opaque string for MVP;
    # a production system would encrypt this field at rest (TRD §8).
    payout_details: Mapped[str] = mapped_column(String(1000), nullable=False)

    # Profile completeness flag – set to True once all required fields are saved
    is_complete: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_now, onupdate=_now
    )

    # Relationships
    user: Mapped[User] = relationship("User", back_populates="supplier_profile")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<SupplierProfile user_id={self.user_id} geography={self.geography}>"
