"""
SQLAlchemy ORM models for Epic 1 & 2.

Entities modelled here mirror TRD §6:
  - users            (id, role, org_id, status)
  - supplier_profiles (user_id, farm metadata, payout metadata)
  - projects         (supplier_id, methodology, geography, status)
  - project_documents (project_id, type, storage_uri, checksum)

Relationships
─────────────
User ──< SupplierProfile   (one-to-one; a supplier has exactly one profile)
User ──< Project            (one-to-many; a supplier may have many projects)
Project ──< ProjectDocument (one-to-many; a project may have many documents)
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

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


class ProjectStatusEnum(str, _enum.Enum):
    draft = "draft"
    submitted = "submitted"
    in_review = "in_review"
    needs_info = "needs_info"
    approved = "approved"
    rejected = "rejected"


class DocumentTypeEnum(str, _enum.Enum):
    registry_evidence = "registry_evidence"
    mrv_record = "mrv_record"
    land_ownership_proof = "land_ownership_proof"
    other = "other"


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
    org_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    status: Mapped[UserStatusEnum] = mapped_column(
        Enum(UserStatusEnum, name="user_status_enum"),
        nullable=False,
        default=UserStatusEnum.pending_verification,
    )
    email_verification_token: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    email_verified_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_now, onupdate=_now
    )

    # Relationships
    supplier_profile: Mapped[Optional["SupplierProfile"]] = relationship(
        "SupplierProfile", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    projects: Mapped[list["Project"]] = relationship(
        "Project", back_populates="supplier", cascade="all, delete-orphan"
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


# ---------------------------------------------------------------------------
# projects
# ---------------------------------------------------------------------------

class Project(Base):
    """
    Carbon credit project submitted by a supplier.

    TRD §5.1 – Project submission form with draft + submitted states.
    TRD §5.2 – Review queue statuses: new, in_review, needs_info, approved, rejected.
    TRD §6   – projects (supplier_id, methodology, geography, status).
    """

    __tablename__ = "projects"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    supplier_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Core project fields (TRD §6)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(2000), nullable=True)
    methodology: Mapped[str] = mapped_column(String(255), nullable=False)
    geography: Mapped[str] = mapped_column(String(255), nullable=False)

    # Lifecycle status
    status: Mapped[ProjectStatusEnum] = mapped_column(
        Enum(ProjectStatusEnum, name="project_status_enum"),
        nullable=False,
        default=ProjectStatusEnum.draft,
    )
    submitted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_now, onupdate=_now
    )

    # Relationships
    supplier: Mapped[User] = relationship("User", back_populates="projects")
    documents: Mapped[list["ProjectDocument"]] = relationship(
        "ProjectDocument", back_populates="project", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Project id={self.id} title={self.title} status={self.status}>"


# ---------------------------------------------------------------------------
# project_documents
# ---------------------------------------------------------------------------

class ProjectDocument(Base):
    """
    Supporting document attached to a carbon credit project.

    TRD §5.1 – Document upload support for registry evidence, MRV records,
                land ownership proofs.
    TRD §6   – project_documents (project_id, type, storage_uri, checksum).
    """

    __tablename__ = "project_documents"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    doc_type: Mapped[DocumentTypeEnum] = mapped_column(
        Enum(DocumentTypeEnum, name="document_type_enum"), nullable=False
    )
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    storage_uri: Mapped[str] = mapped_column(String(1000), nullable=False)
    # SHA-256 hex digest of the uploaded file content
    checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_now
    )

    # Relationships
    project: Mapped[Project] = relationship("Project", back_populates="documents")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<ProjectDocument id={self.id} project_id={self.project_id} type={self.doc_type}>"

