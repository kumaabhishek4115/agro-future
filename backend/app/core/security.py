"""
JWT signing/verification and password hashing utilities.
TRD §4, §8 – authentication required for all non-public endpoints;
              RBAC enforcement on every protected endpoint.
"""

from __future__ import annotations

import base64
from datetime import datetime, timedelta, timezone
from typing import Any

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from jose import jwt
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
_PAYOUT_DETAILS_PREFIX = "enc::"
_payout_fernet = Fernet(
    base64.urlsafe_b64encode(
        HKDF(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b"agro-future-payout-hkdf-salt",
            info=b"agro-future-supplier-payout-details",
        ).derive(settings.PAYOUT_DETAILS_SECRET.encode("utf-8"))
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
    token = _payout_fernet.encrypt(plain.encode("utf-8")).decode("utf-8")
    return f"{_PAYOUT_DETAILS_PREFIX}{token}"


def decrypt_payout_details(encrypted: str | None) -> str | None:
    if encrypted is None:
        return None
    if not encrypted.startswith(_PAYOUT_DETAILS_PREFIX):
        return encrypted
    token = encrypted.removeprefix(_PAYOUT_DETAILS_PREFIX)
    try:
        return _payout_fernet.decrypt(token.encode("utf-8")).decode("utf-8")
    except InvalidToken as exc:
        raise ValueError("Invalid encrypted payout details") from exc
