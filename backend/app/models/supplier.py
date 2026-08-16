"""
Pydantic request / response schemas for supplier profile endpoints.
TRD sections 5.1, 6.
"""

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class OwnershipStatus(str, Enum):
    owned = "owned"
    leased = "leased"
    cooperative = "cooperative"


class SupplierProfileRequest(BaseModel):
    geography: Optional[str] = Field(
        default=None, min_length=1, description="Country / region of the farm"
    )
    land_size_hectares: Optional[float] = Field(
        default=None, gt=0, description="Farm area in hectares"
    )
    crop_or_livestock_type: Optional[str] = Field(default=None, min_length=1)
    ownership_status: Optional[OwnershipStatus] = None
    payout_details: Optional[str] = Field(
        default=None, min_length=1, description="Bank / payment details"
    )

    model_config = {
        "extra": "forbid",
        "json_schema_extra": {
            "example": {
                "geography": "Punjab, India",
                "land_size_hectares": 12.5,
                "crop_or_livestock_type": "Rice",
                "ownership_status": "owned",
                "payout_details": "HDFC Bank ****1234",
            }
        }
    }


class SupplierProfileResponse(BaseModel):
    user_id: str
    geography: Optional[str]
    land_size_hectares: Optional[float]
    crop_or_livestock_type: Optional[str]
    ownership_status: Optional[str]
    payout_details_masked: Optional[str]
    is_complete: bool
    completion_percentage: int
    created_at: str
    updated_at: str

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "user_id": "3f1b1c8e-9f2a-4c1d-8b7e-0d5a2f6c9a11",
                "geography": "Punjab, India",
                "land_size_hectares": 12.5,
                "crop_or_livestock_type": "Rice",
                "ownership_status": "owned",
                "payout_details_masked": "****1234",
                "is_complete": True,
                "completion_percentage": 100,
                "created_at": "2026-08-15T10:00:00+00:00",
                "updated_at": "2026-08-15T10:00:00+00:00",
            }
        },
    }
