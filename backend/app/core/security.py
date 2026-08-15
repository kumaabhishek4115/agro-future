"""
JWT signing/verification and password hashing utilities.
TRD §4, §8 – authentication required for all non-public endpoints;
              RBAC enforcement on every protected endpoint.
"""

from __future__ import annotations

import base64
import hashlib
from datetime import datetime, timedelta, timezone
from typing import Any

from cryptography.fernet import Fernet, InvalidToken
from jose import jwt
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
_payout_fernet = Fernet(
    base64.urlsafe_b64encode(
        hashlib.sha256(settings.PAYOUT_DETAILS_SECRET.encode("utf-8")).digest()
    )
)


def hash_password(plain: str) -> str:
    return pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(data: dict[str, Any]) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    to_encode["exp"] = expire
    return jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any]:
    """Decode and return the JWT payload. Raises JWTError on failure."""
    return jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])


def encrypt_payout_details(plain: str | None) -> str | None:
    if plain is None:
        return None
    return _payout_fernet.encrypt(plain.encode("utf-8")).decode("utf-8")


def decrypt_payout_details(encrypted: str | None) -> str | None:
    if encrypted is None:
        return None
    try:
        return _payout_fernet.decrypt(encrypted.encode("utf-8")).decode("utf-8")
    except InvalidToken:
        return encrypted
