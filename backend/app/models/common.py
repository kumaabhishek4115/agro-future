"""
Shared Pydantic schemas used across routers (OpenAPI error documentation).
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class ErrorResponse(BaseModel):
    """Standard FastAPI error envelope."""

    detail: str = Field(..., description="Human readable error message")

    model_config = {
        "json_schema_extra": {"example": {"detail": "Invalid email or password"}}
    }


class HealthResponse(BaseModel):
    status: str
    service: str

    model_config = {
        "json_schema_extra": {
            "example": {"status": "ok", "service": "agro-future-api"}
        }
    }
