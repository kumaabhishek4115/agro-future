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

    model_config = {"from_attributes": True}
