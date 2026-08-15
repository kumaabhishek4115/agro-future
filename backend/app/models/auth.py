"""
Pydantic request / response schemas for authentication endpoints.
TRD sections 5.1, 7.
"""

from __future__ import annotations

import re
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator

MOBILE_NUMBER_ERROR = (
    "mobile_number must be 7–15 digits with an optional leading '+' "
    "(e.g. +919876543210 or 9876543210). "
    "Spaces are ignored; dashes and parentheses are not supported."
)


def normalize_mobile_number(value: Optional[str]) -> Optional[str]:
    """Strip whitespace and enforce an optional '+' followed by 7–15 digits."""
    if value is None:
        return None
    cleaned = re.sub(r"\s+", "", value)
    if not re.fullmatch(r"\+?[0-9]{7,15}", cleaned):
        raise ValueError(MOBILE_NUMBER_ERROR)
    return cleaned


class RegisterRequest(BaseModel):
    email: Optional[EmailStr] = Field(
        None, description="Required unless mobile_number is provided"
    )
    password: str = Field(..., min_length=8, description="Minimum 8 characters")
    mobile_number: Optional[str] = Field(
        None,
        description="Mobile number in E.164 format, e.g. +919876543210. "
        "Required unless email is provided.",
    )

    @field_validator("mobile_number")
    @classmethod
    def validate_mobile_number(cls, v: Optional[str]) -> Optional[str]:
        return normalize_mobile_number(v)

    @model_validator(mode="after")
    def at_least_one_identifier(self) -> "RegisterRequest":
        if not self.email and not self.mobile_number:
            raise ValueError("Provide at least one of email or mobile_number")
        return self

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
    verification_channel: str = Field(
        ..., description="'email' or 'sms' – where the verification challenge was sent"
    )
    # Returned in the API response for dev/test convenience.
    # In production these are only delivered via email / SMS.
    email_verification_token: Optional[str] = None
    mobile_verification_code: Optional[str] = None

    model_config = {
        "json_schema_extra": {
            "example": {
                "message": "Registration successful. Please check your email to verify your account.",
                "user_id": "3f1b1c8e-9f2a-4c1d-8b7e-0d5a2f6c9a11",
                "verification_channel": "email",
                "email_verification_token": "a4d1f0c2-77bb-4c4e-9a4d-6f2a1b3c5d7e",
                "mobile_verification_code": None,
            }
        }
    }


class VerifyMobileRequest(BaseModel):
    mobile_number: str = Field(..., description="The number the code was sent to")
    code: str = Field(..., min_length=4, max_length=10, description="SMS verification code")

    @field_validator("mobile_number")
    @classmethod
    def validate_mobile_number(cls, v: str) -> str:
        return normalize_mobile_number(v)  # type: ignore[return-value]

    model_config = {
        "json_schema_extra": {
            "example": {"mobile_number": "+919876543210", "code": "483920"}
        }
    }


class ResendMobileCodeRequest(BaseModel):
    mobile_number: str

    @field_validator("mobile_number")
    @classmethod
    def validate_mobile_number(cls, v: str) -> str:
        return normalize_mobile_number(v)  # type: ignore[return-value]

    model_config = {
        "json_schema_extra": {"example": {"mobile_number": "+919876543210"}}
    }


class LoginRequest(BaseModel):
    email: Optional[EmailStr] = Field(
        None, description="Provide either email or mobile_number"
    )
    mobile_number: Optional[str] = Field(
        None, description="Provide either email or mobile_number"
    )
    password: str

    @field_validator("mobile_number")
    @classmethod
    def validate_mobile_number(cls, v: Optional[str]) -> Optional[str]:
        return normalize_mobile_number(v)

    @model_validator(mode="after")
    def exactly_one_identifier(self) -> "LoginRequest":
        if bool(self.email) == bool(self.mobile_number):
            raise ValueError("Provide exactly one of email or mobile_number")
        return self

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
    email: Optional[str] = None
    mobile_number: Optional[str] = None
    role: str

    model_config = {
        "json_schema_extra": {
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer",
                "user_id": "3f1b1c8e-9f2a-4c1d-8b7e-0d5a2f6c9a11",
                "email": "farmer@example.com",
                "mobile_number": "+919876543210",
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
