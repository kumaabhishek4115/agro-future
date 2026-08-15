"""
In-memory store for the MVP.

Mirrors the `users` and `supplier_profiles` entities from TRD §6.
In a production system these would be backed by a relational database
(e.g. PostgreSQL) with the schema described in the TRD.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional


class Role(str, Enum):
    supplier = "supplier"
    buyer = "buyer"
    operator = "operator"
    admin = "admin"


class UserStatus(str, Enum):
    pending_verification = "pending_verification"
    active = "active"
    suspended = "suspended"


class OwnershipStatus(str, Enum):
    owned = "owned"
    leased = "leased"
    cooperative = "cooperative"


@dataclass
class User:
    id: str
    email: str
    password_hash: str
    role: Role
    status: UserStatus
    email_verification_token: Optional[str]
    email_verified_at: Optional[str]
    created_at: str
    updated_at: str


@dataclass
class SupplierProfile:
    user_id: str
    geography: str
    land_size_hectares: float
    crop_or_livestock_type: str
    ownership_status: OwnershipStatus
    payout_details: str
    is_complete: bool
    created_at: str
    updated_at: str


# Singleton in-memory stores (reset per process – suitable for dev / tests)
users_store: dict[str, User] = {}
profiles_store: dict[str, SupplierProfile] = {}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
