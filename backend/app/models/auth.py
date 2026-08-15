"""
Pydantic request / response schemas for authentication endpoints.
TRD sections 5.1, 7.
"""

from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, description="Minimum 8 characters")


class RegisterResponse(BaseModel):
    message: str
    user_id: str
    # Returned in the API response for dev/test convenience.
    # In production this token would only be delivered via email.
    email_verification_token: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    email: str
    role: str


class VerifyEmailRequest(BaseModel):
    token: str = Field(..., min_length=1)


class MessageResponse(BaseModel):
    message: str
