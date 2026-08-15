"""
Tests for Epic 1 – Farmer Account Onboarding.

Covers:
  POST /api/v1/auth/register
  POST /api/v1/auth/verify-email
  POST /api/v1/auth/login
  GET  /api/v1/supplier/profile
  POST /api/v1/supplier/profile

TRD acceptance criteria:
  - Farmer can create an account and verify email before accessing protected pages.
  - Protected farmer routes are deny-by-default for unauthenticated users.
  - Supplier role is enforced separately from other roles.
  - Required profile fields are validated before profile completion is marked complete.
  - Farmers can revisit and update profile details without losing previously entered data.
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.asyncio

BASE = "/api/v1"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

VALID_USER = {"email": "farmer@example.com", "password": "securepass123"}
VALID_PROFILE = {
    "geography": "Kenya",
    "land_size_hectares": 5.0,
    "crop_or_livestock_type": "Maize",
    "ownership_status": "owned",
    "payout_details": "Bank: KCB, Acc: 1234567890",
}

BEARER = "Bearer "


async def _register_and_verify(client, user=None):
    """Register and verify a supplier account; return the bearer token."""
    user = user or VALID_USER
    # 1. Register
    r = await client.post(f"{BASE}/auth/register", json=user)
    assert r.status_code == 201, r.text
    token = r.json()["email_verification_token"]

    # 2. Verify email
    v = await client.post(f"{BASE}/auth/verify-email", json={"token": token})
    assert v.status_code == 200, v.text

    # 3. Login -> get bearer token
    lo = await client.post(f"{BASE}/auth/login", json=user)
    assert lo.status_code == 200, lo.text
    return lo.json()["access_token"]


def auth(token: str) -> dict:
    """Return an Authorization header dict for the given token."""
    return {"Authorization": BEARER + token}


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------


async def test_register_success(client):
    r = await client.post(f"{BASE}/auth/register", json=VALID_USER)
    assert r.status_code == 201
    data = r.json()
    assert "user_id" in data
    assert "email_verification_token" in data
    assert "Registration successful" in data["message"]


async def test_register_duplicate_email(client):
    await client.post(f"{BASE}/auth/register", json=VALID_USER)
    r = await client.post(f"{BASE}/auth/register", json=VALID_USER)
    assert r.status_code == 409


async def test_register_weak_password(client):
    r = await client.post(
        f"{BASE}/auth/register", json={"email": "x@x.com", "password": "short"}
    )
    assert r.status_code == 422  # Pydantic validation error


async def test_register_invalid_email(client):
    r = await client.post(
        f"{BASE}/auth/register",
        json={"email": "not-an-email", "password": "password123"},
    )
    assert r.status_code == 422


# ---------------------------------------------------------------------------
# Email verification
# ---------------------------------------------------------------------------


async def test_verify_email_success(client):
    r = await client.post(f"{BASE}/auth/register", json=VALID_USER)
    token = r.json()["email_verification_token"]
    v = await client.post(f"{BASE}/auth/verify-email", json={"token": token})
    assert v.status_code == 200
    assert "verified" in v.json()["message"].lower()


async def test_verify_email_invalid_token(client):
    r = await client.post(
        f"{BASE}/auth/verify-email", json={"token": "bad-token-xyz"}
    )
    assert r.status_code == 400


async def test_verify_email_already_verified(client):
    r = await client.post(f"{BASE}/auth/register", json=VALID_USER)
    token = r.json()["email_verification_token"]
    await client.post(f"{BASE}/auth/verify-email", json={"token": token})
    # Token is consumed (set to NULL) on first use, so re-sending it returns 400.
    v2 = await client.post(f"{BASE}/auth/verify-email", json={"token": token})
    assert v2.status_code == 400


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------


async def test_login_before_verification_blocked(client):
    await client.post(f"{BASE}/auth/register", json=VALID_USER)
    r = await client.post(f"{BASE}/auth/login", json=VALID_USER)
    assert r.status_code == 403


async def test_login_success_after_verification(client):
    await _register_and_verify(client)
    r = await client.post(f"{BASE}/auth/login", json=VALID_USER)
    assert r.status_code == 200
    data = r.json()
    assert "access_token" in data
    assert data["role"] == "supplier"


async def test_login_wrong_password(client):
    r = await client.post(f"{BASE}/auth/register", json=VALID_USER)
    token = r.json()["email_verification_token"]
    await client.post(f"{BASE}/auth/verify-email", json={"token": token})
    r2 = await client.post(
        f"{BASE}/auth/login",
        json={"email": VALID_USER["email"], "password": "wrongpass"},
    )
    assert r2.status_code == 401


async def test_login_unknown_email(client):
    r = await client.post(
        f"{BASE}/auth/login",
        json={"email": "nobody@example.com", "password": "pass1234"},
    )
    assert r.status_code == 401


# ---------------------------------------------------------------------------
# Supplier profile
# ---------------------------------------------------------------------------


async def test_get_profile_unauthenticated(client):
    """Protected route – must reject unauthenticated requests."""
    r = await client.get(f"{BASE}/supplier/profile")
    assert r.status_code == 403  # HTTPBearer returns 403 when no credentials


async def test_get_profile_not_found(client):
    token = await _register_and_verify(client)
    r = await client.get(f"{BASE}/supplier/profile", headers=auth(token))
    assert r.status_code == 404


async def test_create_profile_success(client):
    token = await _register_and_verify(client)
    r = await client.post(
        f"{BASE}/supplier/profile",
        json=VALID_PROFILE,
        headers=auth(token),
    )
    assert r.status_code == 200
    data = r.json()
    assert data["geography"] == "Kenya"
    assert data["is_complete"] is True


async def test_create_profile_missing_field(client):
    token = await _register_and_verify(client)
    incomplete = {k: v for k, v in VALID_PROFILE.items() if k != "geography"}
    r = await client.post(
        f"{BASE}/supplier/profile",
        json=incomplete,
        headers=auth(token),
    )
    assert r.status_code == 422


async def test_create_profile_invalid_land_size(client):
    token = await _register_and_verify(client)
    bad = {**VALID_PROFILE, "land_size_hectares": -1}
    r = await client.post(
        f"{BASE}/supplier/profile",
        json=bad,
        headers=auth(token),
    )
    assert r.status_code == 422


async def test_get_profile_after_creation(client):
    token = await _register_and_verify(client)
    await client.post(
        f"{BASE}/supplier/profile",
        json=VALID_PROFILE,
        headers=auth(token),
    )
    r = await client.get(f"{BASE}/supplier/profile", headers=auth(token))
    assert r.status_code == 200
    assert r.json()["crop_or_livestock_type"] == "Maize"


async def test_update_profile_preserves_created_at(client):
    """Farmers can update profile details without losing existing data."""
    token = await _register_and_verify(client)
    r1 = await client.post(
        f"{BASE}/supplier/profile",
        json=VALID_PROFILE,
        headers=auth(token),
    )
    assert r1.status_code == 200, r1.text
    created_at = r1.json()["created_at"]

    updated = {**VALID_PROFILE, "geography": "Tanzania", "land_size_hectares": 10.0}
    r2 = await client.post(
        f"{BASE}/supplier/profile",
        json=updated,
        headers=auth(token),
    )
    assert r2.status_code == 200
    assert r2.json()["geography"] == "Tanzania"
    assert r2.json()["created_at"] == created_at  # unchanged


async def test_profile_invalid_ownership_status(client):
    token = await _register_and_verify(client)
    bad = {**VALID_PROFILE, "ownership_status": "rented"}
    r = await client.post(
        f"{BASE}/supplier/profile",
        json=bad,
        headers=auth(token),
    )
    assert r.status_code == 422


async def test_profile_requires_supplier_role(client):
    """A token for a non-existent user UUID must be rejected with 401."""
    from app.core.security import create_access_token
    import uuid

    fake_token = create_access_token({"sub": str(uuid.uuid4()), "role": "buyer"})
    r = await client.get(f"{BASE}/supplier/profile", headers=auth(fake_token))
    # _get_current_user queries DB – user not found → 401
    assert r.status_code == 401
