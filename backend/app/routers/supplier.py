"""
GET  /api/v1/supplier/profile – Fetch the authenticated supplier's profile.
POST /api/v1/supplier/profile – Create or update the supplier profile.

Both endpoints are protected: callers must present a valid bearer token
with role == 'supplier'.  Protected routes are deny-by-default for
unauthenticated users (TRD sections 4, 8).

TRD section 5.1:
  Profile fields: geography, land size, crop/livestock type,
  ownership/lease status, payout details.
TRD section 6:
  supplier_profiles (user_id, farm metadata, payout metadata).
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import SupplierUser
from app.db.models import OwnershipStatusEnum, SupplierProfile, User
from app.db.session import get_db
from app.models.common import ErrorResponse
from app.models.supplier import SupplierProfileRequest, SupplierProfileResponse

router = APIRouter(prefix="/supplier", tags=["supplier"])

PROTECTED_RESPONSES = {
    401: {"model": ErrorResponse, "description": "Missing, invalid or expired bearer token"},
    403: {"model": ErrorResponse, "description": "Supplier role required"},
}


def _profile_to_response(profile: SupplierProfile) -> SupplierProfileResponse:
    return SupplierProfileResponse(
        user_id=str(profile.user_id),
        geography=profile.geography,
        land_size_hectares=profile.land_size_hectares,
        crop_or_livestock_type=profile.crop_or_livestock_type,
        ownership_status=profile.ownership_status.value,
        payout_details=profile.payout_details,
        is_complete=profile.is_complete,
        created_at=profile.created_at.isoformat(),
        updated_at=profile.updated_at.isoformat(),
    )


# ---------------------------------------------------------------------------
# GET /api/v1/supplier/profile
# ---------------------------------------------------------------------------

@router.get(
    "/profile",
    response_model=SupplierProfileResponse,
    summary="Fetch the authenticated supplier's profile",
    responses={
        **PROTECTED_RESPONSES,
        404: {"model": ErrorResponse, "description": "Profile not yet created"},
    },
)
async def get_profile(
    current_user: SupplierUser,
    db: AsyncSession = Depends(get_db),
) -> SupplierProfileResponse:
    """
    Returns the supplier profile for the authenticated farmer.
    Returns 404 if the farmer has not yet completed their profile setup.

    TRD section 5.1 – "Farmers can revisit and update profile details
    without losing previously entered data."
    """
    result = await db.execute(
        select(SupplierProfile).where(SupplierProfile.user_id == current_user.id)
    )
    profile = result.scalar_one_or_none()
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found. Please complete your profile setup.",
        )
    return _profile_to_response(profile)


# ---------------------------------------------------------------------------
# POST /api/v1/supplier/profile
# ---------------------------------------------------------------------------

@router.post(
    "/profile",
    response_model=SupplierProfileResponse,
    summary="Create or update the supplier profile",
    responses={
        **PROTECTED_RESPONSES,
        422: {"model": ErrorResponse, "description": "Validation error"},
    },
)
async def upsert_profile(
    body: SupplierProfileRequest,
    current_user: SupplierUser,
    db: AsyncSession = Depends(get_db),
) -> SupplierProfileResponse:
    """
    Create or fully update the supplier profile.

    Required fields are validated by Pydantic before this handler runs.
    `is_complete` is set to True once all fields are saved.

    TRD section 5.1 – "Required profile fields are validated before profile
    completion is marked complete.  Saved profile data maps cleanly to
    supplier_profiles."
    """
    result = await db.execute(
        select(SupplierProfile).where(SupplierProfile.user_id == current_user.id)
    )
    profile = result.scalar_one_or_none()
    now = datetime.now(timezone.utc)

    if profile is None:
        profile = SupplierProfile(
            user_id=current_user.id,
            geography=body.geography,
            land_size_hectares=body.land_size_hectares,
            crop_or_livestock_type=body.crop_or_livestock_type,
            ownership_status=OwnershipStatusEnum[body.ownership_status.value],
            payout_details=body.payout_details,
            is_complete=True,
            created_at=now,
            updated_at=now,
        )
        db.add(profile)
    else:
        profile.geography = body.geography
        profile.land_size_hectares = body.land_size_hectares
        profile.crop_or_livestock_type = body.crop_or_livestock_type
        profile.ownership_status = OwnershipStatusEnum[body.ownership_status.value]
        profile.payout_details = body.payout_details
        profile.is_complete = True
        profile.updated_at = now

    await db.commit()
    await db.refresh(profile)
    return _profile_to_response(profile)
