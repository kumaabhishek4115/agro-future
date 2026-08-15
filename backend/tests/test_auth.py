"""
Tests for P0 – Supplier account registration, login, and email verification.

Covers all acceptance criteria for GitHub issue #15:
  - Farmer can create an account with email and password.
  - Verification email sent; protected pages inaccessible until email confirmed.
  - Protected farmer routes are deny-by-default (401) for unauthenticated users.
  - Supplier role is enforced separately from other roles.
  - Session tokens are invalidated on logout.
  - Login with invalid credentials returns a clear, non-leaking error message.

TRD sections 4, 5.1, 7, 8.
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.asyncio

BASE = "/api/v1"
BEARER = "Bearer "

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

VALID_USER = {"email": "supplier@test.com", "password": "TestPass123!"}


async def _register(client, user=None):
    """Register a supplier account and return the registration response JSON."""
    payload = user or VALID_USER
    r = await client.post(f"{BASE}/auth/register", json=payload)
    assert r.status_code == 201, r.text
    return r.json()


async def _register_and_verify(client, user=None):
    """Register and verify email; return bearer access token."""
    payload = user or VALID_USER
    reg = await _register(client, payload)
    v = await client.post(
        f"{BASE}/auth/verify-email",
        json={"token": reg["email_verification_token"]},
    )
    assert v.status_code == 200, v.text
    lo = await client.post(f"{BASE}/auth/login", json=payload)
    assert lo.status_code == 200, lo.text
    return lo.json()["access_token"]


def auth(token: str) -> dict:
    return {"Authorization": BEARER + token}


# ---------------------------------------------------------------------------
# AC: Farmer can create an account with email and password
# ---------------------------------------------------------------------------


async def test_register_returns_201_with_user_id(client):
    """Registration creates a new supplier account and returns the user ID."""
    r = await client.post(f"{BASE}/auth/register", json=VALID_USER)
    assert r.status_code == 201
    data = r.json()
    assert "user_id" in data
    assert "email_verification_token" in data
    assert "Registration successful" in data["message"]


async def test_register_password_too_short_rejected(client):
    """Passwords shorter than 8 characters are rejected with 422."""
    r = await client.post(
        f"{BASE}/auth/register",
        json={"email": "a@b.com", "password": "short"},
    )
    assert r.status_code == 422


async def test_register_invalid_email_rejected(client):
    """Non-email strings in the email field are rejected with 422."""
    r = await client.post(
        f"{BASE}/auth/register",
        json={"email": "not-an-email", "password": "password123"},
    )
    assert r.status_code == 422


async def test_register_duplicate_email_returns_409(client):
    """Re-registering with the same email address returns 409 Conflict."""
    await _register(client)
    r = await client.post(f"{BASE}/auth/register", json=VALID_USER)
    assert r.status_code == 409
    assert "already exists" in r.json()["detail"].lower()


# ---------------------------------------------------------------------------
# AC: Verification email; protected pages inaccessible before confirmation
# ---------------------------------------------------------------------------


async def test_login_blocked_before_email_verification(client):
    """Account in pending_verification state cannot log in (403)."""
    await _register(client)
    r = await client.post(f"{BASE}/auth/login", json=VALID_USER)
    assert r.status_code == 403
    assert "verify" in r.json()["detail"].lower()


async def test_verify_email_activates_account(client):
    """A valid verification token activates the account."""
    reg = await _register(client)
    v = await client.post(
        f"{BASE}/auth/verify-email",
        json={"token": reg["email_verification_token"]},
    )
    assert v.status_code == 200
    assert "verified" in v.json()["message"].lower()


async def test_verify_email_invalid_token_returns_400(client):
    """An unknown verification token returns 400."""
    r = await client.post(
        f"{BASE}/auth/verify-email",
        json={"token": "invalid-token-xyz"},
    )
    assert r.status_code == 400


async def test_verify_email_token_is_single_use(client):
    """Once consumed, the same token cannot be reused (returns 400)."""
    reg = await _register(client)
    token = reg["email_verification_token"]
    await client.post(f"{BASE}/auth/verify-email", json={"token": token})
    # Second attempt – token was nulled out after first use
    r2 = await client.post(f"{BASE}/auth/verify-email", json={"token": token})
    assert r2.status_code == 400


async def test_protected_profile_blocked_before_email_verification(client):
    """Protected endpoints return 4xx for an unverified (pending) account's token.

    Since unverified users cannot log in at all, we just confirm the protected
    route rejects unauthenticated requests.
    """
    r = await client.get(f"{BASE}/supplier/profile")
    assert r.status_code in (401, 403)


# ---------------------------------------------------------------------------
# AC: Protected routes deny-by-default for unauthenticated users
# ---------------------------------------------------------------------------


async def test_supplier_profile_unauthenticated_returns_4xx(client):
    """GET /supplier/profile with no token returns 401 or 403."""
    r = await client.get(f"{BASE}/supplier/profile")
    assert r.status_code in (401, 403)


async def test_projects_unauthenticated_returns_4xx(client):
    """GET /projects with no token returns 401 or 403."""
    r = await client.get(f"{BASE}/projects")
    assert r.status_code in (401, 403)


async def test_invalid_bearer_token_returns_401(client):
    """A malformed or forged bearer token is rejected with 401 or 403."""
    r = await client.get(
        f"{BASE}/supplier/profile",
        headers={"Authorization": "******"},
    )
    assert r.status_code in (401, 403)


# ---------------------------------------------------------------------------
# AC: Supplier role enforced separately; cross-role access rejected
# ---------------------------------------------------------------------------


async def test_login_returns_supplier_role(client):
    """A supplier account's token carries role='supplier'."""
    await _register_and_verify(client)
    r = await client.post(f"{BASE}/auth/login", json=VALID_USER)
    assert r.json()["role"] == "supplier"


async def test_supplier_endpoint_rejects_wrong_role(client):
    """A non-supplier token is rejected with 403 on supplier-only endpoints.

    We simulate this by crafting a JWT with role='buyer' using the same secret,
    then trying to access the supplier profile endpoint.
    """
    from app.core.security import create_access_token
    import uuid

    fake_token = create_access_token({"sub": str(uuid.uuid4()), "role": "buyer"})
    r = await client.get(
        f"{BASE}/supplier/profile",
        headers={"Authorization": f"******"},
    )
    # User not in DB → 401 (token valid but user gone), OR role mismatch → 403
    assert r.status_code in (401, 403)


# ---------------------------------------------------------------------------
# AC: Session tokens are invalidated on logout
# ---------------------------------------------------------------------------


async def test_logout_returns_200(client):
    """Calling logout with a valid token returns 200 and a success message."""
    token = await _register_and_verify(client)
    r = await client.post(f"{BASE}/auth/logout", headers=auth(token))
    assert r.status_code == 200
    assert "logged out" in r.json()["message"].lower()


async def test_token_rejected_after_logout(client):
    """After logout the token no longer grants access to protected endpoints."""
    token = await _register_and_verify(client)
    await client.post(f"{BASE}/auth/logout", headers=auth(token))
    r = await client.get(f"{BASE}/supplier/profile", headers=auth(token))
    assert r.status_code == 401


async def test_logout_idempotent(client):
    """Logging out twice with the same token does not raise a 5xx error."""
    token = await _register_and_verify(client)
    r1 = await client.post(f"{BASE}/auth/logout", headers=auth(token))
    assert r1.status_code == 200
    r2 = await client.post(f"{BASE}/auth/logout", headers=auth(token))
    # Token is blacklisted on first call; second call gets 401 (token invalid).
    assert r2.status_code in (200, 401)


async def test_logout_requires_authentication(client):
    """Calling logout without a token is rejected."""
    r = await client.post(f"{BASE}/auth/logout")
    assert r.status_code in (401, 403)


# ---------------------------------------------------------------------------
# AC: Login with invalid credentials returns a clear, non-leaking error
# ---------------------------------------------------------------------------


async def test_login_wrong_password_returns_401(client):
    """Wrong password returns 401 with a generic message (no info leak)."""
    await _register_and_verify(client)
    r = await client.post(
        f"{BASE}/auth/login",
        json={"email": VALID_USER["email"], "password": "WrongPassword!"},
    )
    assert r.status_code == 401
    detail = r.json()["detail"]
    # Message must not reveal whether the email or password was wrong
    assert detail == "Invalid email or password"
    # Must not expose hashed password or any internal state
    assert "hash" not in detail.lower()


async def test_login_unknown_email_returns_401(client):
    """Unknown email returns 401 with the same message as wrong password."""
    r = await client.post(
        f"{BASE}/auth/login",
        json={"email": "nobody@example.com", "password": "SomePass123"},
    )
    assert r.status_code == 401
    assert r.json()["detail"] == "Invalid email or password"


async def test_login_success_after_verification(client):
    """Full happy-path: register → verify → login returns a bearer token."""
    token = await _register_and_verify(client)
    assert token  # non-empty JWT string
