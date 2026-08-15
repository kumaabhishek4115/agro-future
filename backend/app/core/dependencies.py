"""
FastAPI dependency that extracts and validates the bearer token from the
Authorization header and enforces role-based access control.

TRD section 4  - Access control must be role-based, deny-by-default.
TRD section 8  - Authentication required for all non-public endpoints;
                 RBAC enforcement on every protected endpoint.
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_access_token
from app.db.models import RoleEnum, User
from app.db.session import get_db

bearer_scheme = HTTPBearer(
    auto_error=True,
    scheme_name="BearerAuth",
    description="Paste the `access_token` returned by POST /api/v1/auth/login",
)


async def _get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(bearer_scheme)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    """Validate JWT and return the corresponding User row from PostgreSQL."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_access_token(credentials.credentials)
        user_id_str: str | None = payload.get("sub")
        if user_id_str is None:
            raise credentials_exception
        user_id = uuid.UUID(user_id_str)
    except Exception:
        raise credentials_exception

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise credentials_exception
    return user


# Re-usable annotated dependency
CurrentUser = Annotated[User, Depends(_get_current_user)]


def require_supplier(current_user: CurrentUser) -> User:
    """Allow only users with the 'supplier' role."""
    if current_user.role != RoleEnum.supplier:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Supplier role required",
        )
    return current_user


SupplierUser = Annotated[User, Depends(require_supplier)]
