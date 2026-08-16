"""
Reusable authorization helpers for tenant-aware resource access checks.

TRD sections 4, 8, 10.
"""

from __future__ import annotations

import uuid

from fastapi import HTTPException, status


def ensure_supplier_owns_resource(
    *,
    resource_owner_id: uuid.UUID,
    current_user_id: uuid.UUID,
    resource_name: str,
) -> None:
    """Raise 403 when a supplier attempts to access another supplier's resource."""
    if resource_owner_id != current_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Forbidden: cannot access another supplier's {resource_name}.",
        )
