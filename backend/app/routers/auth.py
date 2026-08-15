"""
POST /api/v1/auth/register   – Supplier account registration.
POST /api/v1/auth/login      – Return a signed JWT.
POST /api/v1/auth/verify-email – Activate account from email token.
POST /api/v1/auth/logout     – Invalidate the current session token.

TRD sections 4, 5.1, 7, 8.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.dependencies import CurrentUser, bearer_scheme
from app.core.security import create_access_token, hash_password, verify_password, decode_access_token
from app.db.models import BlacklistedToken, RoleEnum, User, UserStatusEnum
from app.db.session import get_db
from app.models.auth import (
    LoginRequest,
    MessageResponse,
    RegisterRequest,
    RegisterResponse,
    TokenResponse,
    VerifyEmailRequest,
)
from app.models.common import ErrorResponse

router = APIRouter(prefix="/auth", tags=["auth"])


# ---------------------------------------------------------------------------
# POST /api/v1/auth/register
# ---------------------------------------------------------------------------

@router.post(
    "/register",
    response_model=RegisterResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new supplier account",
    responses={
        409: {"model": ErrorResponse, "description": "Email already registered"},
        422: {"model": ErrorResponse, "description": "Validation error"},
    },
)
async def register(
    body: RegisterRequest,
    db: AsyncSession = Depends(get_db),
) -> RegisterResponse:
    """
    Create a new supplier account with `pending_verification` status.

    The returned `email_verification_token` is normally delivered via email.
    It is exposed in the response body only for development / testing convenience.
    Farmers cannot log in until they verify their email address.

    TRD section 5.1 – "Supplier account registration with email verification."
    """
    # Uniqueness check (also enforced at DB level by the unique index)
    existing = await db.execute(
        select(User).where(User.email == body.email.lower())
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with that email already exists",
        )

    verification_token = str(uuid.uuid4())
    user = User(
        email=body.email.lower(),
        password_hash=hash_password(body.password),
        role=RoleEnum.supplier,
        status=UserStatusEnum.pending_verification,
        email_verification_token=verification_token,
    )
    db.add(user)
    try:
        await db.commit()
        await db.refresh(user)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with that email already exists",
        )

    return RegisterResponse(
        message=(
            "Registration successful. "
            "Please check your email to verify your account."
        ),
        user_id=str(user.id),
        email_verification_token=verification_token,
    )


# ---------------------------------------------------------------------------
# POST /api/v1/auth/login
# ---------------------------------------------------------------------------

@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Log in and receive a bearer token",
    responses={
        401: {"model": ErrorResponse, "description": "Invalid email or password"},
        403: {"model": ErrorResponse, "description": "Email not verified or account suspended"},
    },
)
async def login(
    body: LoginRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """
    Authenticate with email and password.
    Returns a signed JWT that must be sent as `Authorization: ******
    on all protected endpoints.

    TRD section 4 – role-based, deny-by-default access control.
    """
    result = await db.execute(select(User).where(User.email == body.email.lower()))
    user = result.scalar_one_or_none()

    if user is None or not verify_password(body.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if user.status == UserStatusEnum.pending_verification:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Please verify your email before logging in",
        )
    if user.status == UserStatusEnum.suspended:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account suspended. Contact support.",
        )

    token = create_access_token({"sub": str(user.id), "role": user.role.value})
    return TokenResponse(
        access_token=token,
        user_id=str(user.id),
        email=user.email,
        role=user.role.value,
    )


# ---------------------------------------------------------------------------
# POST /api/v1/auth/verify-email
# ---------------------------------------------------------------------------

@router.post(
    "/verify-email",
    response_model=MessageResponse,
    summary="Verify email address and activate the account",
    responses={
        400: {"model": ErrorResponse, "description": "Invalid or expired verification token"},
    },
)
async def verify_email(
    body: VerifyEmailRequest,
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    """
    Activate a supplier account once the user clicks the verification link.

    TRD section 5.1 – "email verification before accessing protected portal pages."
    """
    result = await db.execute(
        select(User).where(User.email_verification_token == body.token)
    )
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification token",
        )

    if user.email_verified_at is not None:
        return MessageResponse(message="Email already verified")

    user.status = UserStatusEnum.active
    user.email_verified_at = datetime.now(timezone.utc)
    user.email_verification_token = None
    await db.commit()

    return MessageResponse(message="Email verified successfully. You may now log in.")


# ---------------------------------------------------------------------------
# POST /api/v1/auth/logout
# ---------------------------------------------------------------------------

@router.post(
    "/logout",
    response_model=MessageResponse,
    summary="Invalidate the current session token",
    responses={
        401: {"model": ErrorResponse, "description": "Missing or invalid token"},
    },
)
async def logout(
    current_user: CurrentUser,
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    """
    Invalidate the caller's JWT by adding it to the server-side blacklist.

    After this call the token is rejected by every protected endpoint, even if
    it has not yet reached its natural expiry time.

    TRD §8 – session tokens must be invalidated on logout.
    """
    raw_token = credentials.credentials
    # Best-effort: extract expiry from the decoded token for future cleanup.
    expires_at = None
    try:
        payload = decode_access_token(raw_token)
        exp = payload.get("exp")
        if exp is not None:
            expires_at = datetime.fromtimestamp(exp, tz=timezone.utc)
    except Exception:
        pass  # Already validated by CurrentUser; ignore decode errors here.

    db.add(BlacklistedToken(token=raw_token, expires_at=expires_at))
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        # Token already blacklisted – idempotent logout is fine.

    return MessageResponse(message="Logged out successfully")
