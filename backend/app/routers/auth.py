"""
POST /api/v1/auth/register   – Supplier account registration.
POST /api/v1/auth/login      – Return a signed JWT.
POST /api/v1/auth/verify-email – Activate account from email token.
POST /api/v1/auth/verify-mobile – Activate account from SMS code.
POST /api/v1/auth/resend-mobile-code – Issue a fresh SMS code.
POST /api/v1/auth/logout     – Invalidate the current session token.

TRD sections 4, 5.1, 7, 8.
"""

from __future__ import annotations

import secrets
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.dependencies import CurrentUser, bearer_scheme
from app.core.email import email_service
from app.core.security import create_access_token, hash_password, verify_password, decode_access_token
from app.core.sms import sms_service
from app.db.models import BlacklistedToken, RoleEnum, User, UserStatusEnum
from app.db.session import get_db
from app.models.auth import (
    LoginRequest,
    MessageResponse,
    RegisterRequest,
    RegisterResponse,
    ResendMobileCodeRequest,
    TokenResponse,
    VerifyEmailRequest,
    VerifyMobileRequest,
)
from app.models.common import ErrorResponse

router = APIRouter(prefix="/auth", tags=["auth"])


def generate_mobile_code() -> str:
    """Six-digit numeric one-time code."""
    return f"{secrets.randbelow(1_000_000):06d}"


def mobile_code_expiry() -> datetime:
    return datetime.now(timezone.utc) + timedelta(
        minutes=settings.MOBILE_CODE_TTL_MINUTES
    )


def _as_utc(value: datetime) -> datetime:
    """SQLite returns naive datetimes; assume stored values are UTC."""
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


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

    Sign-up works with an email address (verification link) or a mobile number
    (SMS one-time code). When both are given, the email link is the challenge.
    The token / code are echoed in the response for development convenience
    only; in production they are delivered out of band. Farmers cannot log in
    until one channel is verified.

    TRD section 5.1 – "Supplier account registration with email verification."
    """
    email = body.email.lower() if body.email else None

    # Uniqueness checks (also enforced at DB level by the unique indexes)
    if email:
        existing = await db.execute(select(User).where(User.email == email))
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="An account with that email already exists",
            )

    if body.mobile_number:
        existing_mobile = await db.execute(
            select(User).where(User.mobile_number == body.mobile_number)
        )
        if existing_mobile.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="An account with that mobile number already exists",
            )

    use_email = email is not None
    verification_token = str(uuid.uuid4()) if use_email else None
    mobile_code = None if use_email else generate_mobile_code()

    user = User(
        email=email,
        mobile_number=body.mobile_number,
        password_hash=hash_password(body.password),
        role=RoleEnum.supplier,
        status=UserStatusEnum.pending_verification,
        email_verification_token=verification_token,
        mobile_verification_code=hash_password(mobile_code) if mobile_code else None,
        mobile_code_expires_at=mobile_code_expiry() if mobile_code else None,
    )
    db.add(user)
    try:
        await db.commit()
        await db.refresh(user)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with those details already exists",
        )

    if use_email:
        await email_service.send_verification_email(
            to_address=user.email, token=verification_token
        )
        message = (
            "Registration successful. "
            "Please check your email to verify your account."
        )
    else:
        await sms_service.send_verification_code(
            to_number=user.mobile_number, code=mobile_code
        )
        message = (
            "Registration successful. "
            "Enter the code we sent by SMS to verify your account."
        )

    return RegisterResponse(
        message=message,
        user_id=str(user.id),
        verification_channel="email" if use_email else "sms",
        email_verification_token=verification_token,
        mobile_verification_code=mobile_code,
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
    Authenticate with email or mobile number, plus password.
    Returns a signed JWT that must be sent as `Authorization: ******
    on all protected endpoints.

    TRD section 4 – role-based, deny-by-default access control.
    """
    if body.email:
        lookup = User.email == body.email.lower()
    else:
        lookup = User.mobile_number == body.mobile_number

    result = await db.execute(select(User).where(lookup))
    user = result.scalar_one_or_none()

    if user is None or not verify_password(body.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if user.status == UserStatusEnum.pending_verification:
        channel = "email" if user.email_verification_token else "mobile number"
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Please verify your {channel} before logging in",
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
        mobile_number=user.mobile_number,
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
# POST /api/v1/auth/verify-mobile
# ---------------------------------------------------------------------------

@router.post(
    "/verify-mobile",
    response_model=MessageResponse,
    summary="Verify a mobile number with the SMS code and activate the account",
    responses={
        400: {"model": ErrorResponse, "description": "Invalid or expired verification code"},
    },
)
async def verify_mobile(
    body: VerifyMobileRequest,
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    """Activate an account signed up with a mobile number (TRD section 5.1)."""
    invalid = HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Invalid or expired verification code",
    )

    result = await db.execute(
        select(User).where(User.mobile_number == body.mobile_number)
    )
    user = result.scalar_one_or_none()
    if user is None:
        raise invalid

    if user.mobile_verified_at is not None:
        return MessageResponse(message="Mobile number already verified")

    if (
        user.mobile_verification_code is None
        or user.mobile_code_expires_at is None
        or _as_utc(user.mobile_code_expires_at) < datetime.now(timezone.utc)
        or not verify_password(body.code, user.mobile_verification_code)
    ):
        raise invalid

    user.status = UserStatusEnum.active
    user.mobile_verified_at = datetime.now(timezone.utc)
    user.mobile_verification_code = None
    user.mobile_code_expires_at = None
    await db.commit()

    return MessageResponse(
        message="Mobile number verified successfully. You may now log in."
    )


# ---------------------------------------------------------------------------
# POST /api/v1/auth/resend-mobile-code
# ---------------------------------------------------------------------------

@router.post(
    "/resend-mobile-code",
    response_model=MessageResponse,
    summary="Send a fresh SMS verification code",
)
async def resend_mobile_code(
    body: ResendMobileCodeRequest,
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    """
    Issue a new one-time code. The response is identical whether or not the
    number exists, so it cannot be used to enumerate accounts.
    """
    generic = MessageResponse(
        message="If that number is registered, a verification code has been sent."
    )

    result = await db.execute(
        select(User).where(User.mobile_number == body.mobile_number)
    )
    user = result.scalar_one_or_none()
    if user is None or user.mobile_verified_at is not None:
        return generic

    code = generate_mobile_code()
    user.mobile_verification_code = hash_password(code)
    user.mobile_code_expires_at = mobile_code_expiry()
    await db.commit()

    await sms_service.send_verification_code(to_number=user.mobile_number, code=code)
    return generic


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
