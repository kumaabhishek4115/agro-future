"""
Pydantic request / response schemas for supplier profile endpoints.
TRD sections 5.1, 6.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class OwnershipStatus(str, Enum):
    owned = "owned"
    leased = "leased"
    cooperative = "cooperative"


class SupplierProfileRequest(BaseModel):
    geography: str = Field(..., min_length=1, description="Country / region of the farm")
    land_size_hectares: float = Field(..., gt=0, description="Farm area in hectares")
    crop_or_livestock_type: str = Field(..., min_length=1)
    ownership_status: OwnershipStatus
    payout_details: str = Field(..., min_length=1, description="Bank / payment details")

    model_config = {
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
    geography: str
    land_size_hectares: float
    crop_or_livestock_type: str
    ownership_status: str
    payout_details: str
    is_complete: bool
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
                "payout_details": "HDFC Bank ****1234",
                "is_complete": True,
                "created_at": "2026-08-15T10:00:00+00:00",
                "updated_at": "2026-08-15T10:00:00+00:00",
            }
        },
    }
