"""
FastAPI dependency that extracts and validates the ****** from the
Authorization header and enforces role-based access control.

TRD §4 – "Access control must be role-based, deny-by-default."
TRD §8 – "Authentication required for all non-public endpoints;
           RBAC enforcement on every protected endpoint."
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.security import decode_access_token
from app.db.store import Role, User, users_store

bearer_scheme = HTTPBearer(auto_error=True)


def _get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(bearer_scheme)],
) -> User:
    """Validate JWT and return the corresponding User object."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_access_token(credentials.credentials)
        user_id: str | None = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except Exception:
        raise credentials_exception

    user = users_store.get(user_id)
    if user is None:
        raise credentials_exception
    return user


# Re-usable annotated dependency
CurrentUser = Annotated[User, Depends(_get_current_user)]


def require_supplier(current_user: CurrentUser) -> User:
    """Allow only users with the 'supplier' role."""
    if current_user.role != Role.supplier:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Supplier role required",
        )
    return current_user


SupplierUser = Annotated[User, Depends(require_supplier)]
