"""
Pydantic request / response schemas for authentication endpoints.
TRD sections 5.1, 7.
"""

from __future__ import annotations

import re
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, field_validator


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, description="Minimum 8 characters")
    mobile_number: Optional[str] = Field(
        None,
        description="Optional mobile number in E.164 format, e.g. +919876543210",
    )

    @field_validator("mobile_number")
    @classmethod
    def validate_mobile_number(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        # Strip whitespace only; do not normalise dashes/parentheses so that
        # callers are clear that strict E.164-style digits are expected.
        cleaned = re.sub(r"\s+", "", v)
        # Accept an optional leading '+' followed by 7–15 digits (E.164 range).
        # Numbers without a leading '+' are also accepted (e.g. local formats).
        if not re.fullmatch(r"\+?[0-9]{7,15}", cleaned):
            raise ValueError(
                "mobile_number must be 7–15 digits with an optional leading '+' "
                "(e.g. +919876543210 or 9876543210). "
                "Spaces are ignored; dashes and parentheses are not supported."
            )
        return cleaned

    model_config = {
        "json_schema_extra": {
            "example": {
                "email": "farmer@example.com",
                "password": "StrongPassw0rd!",
                "mobile_number": "+919876543210",
            }
        }
    }


class RegisterResponse(BaseModel):
    message: str
    user_id: str
    # Returned in the API response for dev/test convenience.
    # In production this token would only be delivered via email.
    email_verification_token: str

    model_config = {
        "json_schema_extra": {
            "example": {
                "message": "Registration successful. Please check your email to verify your account.",
                "user_id": "3f1b1c8e-9f2a-4c1d-8b7e-0d5a2f6c9a11",
                "email_verification_token": "a4d1f0c2-77bb-4c4e-9a4d-6f2a1b3c5d7e",
            }
        }
    }


class LoginRequest(BaseModel):
    email: EmailStr
    password: str

    model_config = {
        "json_schema_extra": {
            "example": {
                "email": "farmer@example.com",
                "password": "StrongPassw0rd!",
            }
        }
    }


class TokenResponse(BaseModel):
    access_token: str = Field(..., description="Signed JWT; send as `Authorization: Bearer <token>`")
    token_type: str = "bearer"
    user_id: str
    email: str
    role: str

    model_config = {
        "json_schema_extra": {
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer",
                "user_id": "3f1b1c8e-9f2a-4c1d-8b7e-0d5a2f6c9a11",
                "email": "farmer@example.com",
                "role": "supplier",
            }
        }
    }


class VerifyEmailRequest(BaseModel):
    token: str = Field(..., min_length=1, description="Token emailed at registration")

    model_config = {
        "json_schema_extra": {
            "example": {"token": "a4d1f0c2-77bb-4c4e-9a4d-6f2a1b3c5d7e"}
        }
    }


class MessageResponse(BaseModel):
    message: str

    model_config = {
        "json_schema_extra": {
            "example": {"message": "Email verified successfully. You may now log in."}
        }
    }
