"""
Tests for Epic 2 – Project Intake and Document Submission.

Covers:
  POST   /api/v1/projects
  GET    /api/v1/projects
  GET    /api/v1/projects/{project_id}
  PATCH  /api/v1/projects/{project_id}
  POST   /api/v1/projects/{project_id}/submit
  POST   /api/v1/projects/{project_id}/documents
  GET    /api/v1/projects/{project_id}/documents

TRD acceptance criteria (§5.1, §5.2):
  - Farmers can create a carbon credit project in draft state.
  - Draft projects can be partially updated without losing data.
  - Projects can be submitted; submitted projects enter the review queue.
  - Supporting documents can be uploaded and listed.
  - Validation rules are enforced before submission.
  - All endpoints are deny-by-default for unauthenticated requests.
"""

from __future__ import annotations

import io
import uuid

import pytest

pytestmark = pytest.mark.asyncio

BASE = "/api/v1"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

VALID_USER = {"email": "farmer2@example.com", "password": "securepass123"}

VALID_PROJECT = {
    "title": "Rice Field Carbon Sequestration",
    "description": "Improved paddy management reducing CH4 emissions.",
    "methodology": "VM0015",
    "geography": "Punjab, India",
}

BEARER = "Bearer "


async def _register_and_verify(client, user=None):
    """Register and verify a supplier account; return the bearer token."""
    user = user or VALID_USER
    r = await client.post(f"{BASE}/auth/register", json=user)
    assert r.status_code == 201, r.text
    token = r.json()["email_verification_token"]
    v = await client.post(f"{BASE}/auth/verify-email", json={"token": token})
    assert v.status_code == 200, v.text
    lo = await client.post(f"{BASE}/auth/login", json=user)
    assert lo.status_code == 200, lo.text
    return lo.json()["access_token"]


def auth(token: str) -> dict:
    return {"Authorization": BEARER + token}


async def _create_project(client, token, data=None):
    data = data or VALID_PROJECT
    r = await client.post(f"{BASE}/projects", json=data, headers=auth(token))
    assert r.status_code == 201, r.text
    return r.json()


# ---------------------------------------------------------------------------
# Authentication / authorization
# ---------------------------------------------------------------------------


async def test_create_project_unauthenticated(client):
    r = await client.post(f"{BASE}/projects", json=VALID_PROJECT)
    assert r.status_code == 403


async def test_list_projects_unauthenticated(client):
    r = await client.get(f"{BASE}/projects")
    assert r.status_code == 403


# ---------------------------------------------------------------------------
# Draft creation
# ---------------------------------------------------------------------------


async def test_create_project_success(client):
    token = await _register_and_verify(client)
    r = await client.post(f"{BASE}/projects", json=VALID_PROJECT, headers=auth(token))
    assert r.status_code == 201
    data = r.json()
    assert data["title"] == VALID_PROJECT["title"]
    assert data["status"] == "draft"
    assert data["submitted_at"] is None
    assert "id" in data
    assert "created_at" in data


async def test_create_project_missing_required_field(client):
    token = await _register_and_verify(client)
    bad = {k: v for k, v in VALID_PROJECT.items() if k != "title"}
    r = await client.post(f"{BASE}/projects", json=bad, headers=auth(token))
    assert r.status_code == 422


async def test_create_project_without_description(client):
    """description is optional."""
    token = await _register_and_verify(client)
    no_desc = {k: v for k, v in VALID_PROJECT.items() if k != "description"}
    r = await client.post(f"{BASE}/projects", json=no_desc, headers=auth(token))
    assert r.status_code == 201
    assert r.json()["description"] is None


# ---------------------------------------------------------------------------
# Listing
# ---------------------------------------------------------------------------


async def test_list_projects_empty(client):
    token = await _register_and_verify(client)
    r = await client.get(f"{BASE}/projects", headers=auth(token))
    assert r.status_code == 200
    assert r.json() == []


async def test_list_projects_returns_own_projects_only(client):
    token1 = await _register_and_verify(client, {"email": "farmer_a@example.com", "password": "pass12345"})
    token2 = await _register_and_verify(client, {"email": "farmer_b@example.com", "password": "pass12345"})

    await _create_project(client, token1)
    await _create_project(client, token1)
    await _create_project(client, token2)  # belongs to farmer_b

    r = await client.get(f"{BASE}/projects", headers=auth(token1))
    assert r.status_code == 200
    assert len(r.json()) == 2

    r2 = await client.get(f"{BASE}/projects", headers=auth(token2))
    assert len(r2.json()) == 1


# ---------------------------------------------------------------------------
# Get single project
# ---------------------------------------------------------------------------


async def test_get_project_success(client):
    token = await _register_and_verify(client)
    project = await _create_project(client, token)
    r = await client.get(f"{BASE}/projects/{project['id']}", headers=auth(token))
    assert r.status_code == 200
    assert r.json()["id"] == project["id"]


async def test_get_project_not_found(client):
    token = await _register_and_verify(client)
    r = await client.get(f"{BASE}/projects/{uuid.uuid4()}", headers=auth(token))
    assert r.status_code == 404


async def test_get_project_cross_user_forbidden(client):
    """A supplier cannot access another supplier's project."""
    token1 = await _register_and_verify(client, {"email": "c_a@example.com", "password": "pass12345"})
    token2 = await _register_and_verify(client, {"email": "c_b@example.com", "password": "pass12345"})
    project = await _create_project(client, token1)
    r = await client.get(f"{BASE}/projects/{project['id']}", headers=auth(token2))
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# Update (PATCH)
# ---------------------------------------------------------------------------


async def test_update_project_success(client):
    token = await _register_and_verify(client)
    project = await _create_project(client, token)
    r = await client.patch(
        f"{BASE}/projects/{project['id']}",
        json={"geography": "Haryana, India"},
        headers=auth(token),
    )
    assert r.status_code == 200
    assert r.json()["geography"] == "Haryana, India"
    # Other fields unchanged
    assert r.json()["title"] == VALID_PROJECT["title"]


async def test_update_project_preserves_created_at(client):
    token = await _register_and_verify(client)
    project = await _create_project(client, token)
    created_at = project["created_at"]
    r = await client.patch(
        f"{BASE}/projects/{project['id']}",
        json={"methodology": "AMS-III.AU"},
        headers=auth(token),
    )
    assert r.status_code == 200
    assert r.json()["created_at"] == created_at


async def test_update_submitted_project_rejected(client):
    """Submitted projects cannot be edited."""
    token = await _register_and_verify(client)
    project = await _create_project(client, token)
    # Submit first
    await client.post(f"{BASE}/projects/{project['id']}/submit", headers=auth(token))
    # Attempt update
    r = await client.patch(
        f"{BASE}/projects/{project['id']}",
        json={"geography": "New Place"},
        headers=auth(token),
    )
    assert r.status_code == 409


# ---------------------------------------------------------------------------
# Submission
# ---------------------------------------------------------------------------


async def test_submit_project_success(client):
    token = await _register_and_verify(client)
    project = await _create_project(client, token)
    r = await client.post(
        f"{BASE}/projects/{project['id']}/submit", headers=auth(token)
    )
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "submitted"
    assert data["submitted_at"] is not None


async def test_submit_already_submitted(client):
    token = await _register_and_verify(client)
    project = await _create_project(client, token)
    await client.post(f"{BASE}/projects/{project['id']}/submit", headers=auth(token))
    r = await client.post(
        f"{BASE}/projects/{project['id']}/submit", headers=auth(token)
    )
    assert r.status_code == 409


# ---------------------------------------------------------------------------
# Document upload
# ---------------------------------------------------------------------------


async def test_upload_document_success(client):
    token = await _register_and_verify(client)
    project = await _create_project(client, token)
    file_content = b"Sample registry evidence document content."
    r = await client.post(
        f"{BASE}/projects/{project['id']}/documents",
        headers=auth(token),
        data={"doc_type": "registry_evidence"},
        files={"file": ("evidence.pdf", io.BytesIO(file_content), "application/pdf")},
    )
    assert r.status_code == 201
    data = r.json()
    assert data["doc_type"] == "registry_evidence"
    assert data["filename"] == "evidence.pdf"
    assert len(data["checksum"]) == 64  # SHA-256 hex
    assert data["project_id"] == project["id"]


async def test_upload_document_invalid_type(client):
    token = await _register_and_verify(client)
    project = await _create_project(client, token)
    r = await client.post(
        f"{BASE}/projects/{project['id']}/documents",
        headers=auth(token),
        data={"doc_type": "invalid_type"},
        files={"file": ("doc.pdf", io.BytesIO(b"content"), "application/pdf")},
    )
    assert r.status_code == 422


async def test_upload_document_to_submitted_project_rejected(client):
    """Documents cannot be uploaded to an already-submitted project."""
    token = await _register_and_verify(client)
    project = await _create_project(client, token)
    await client.post(f"{BASE}/projects/{project['id']}/submit", headers=auth(token))
    r = await client.post(
        f"{BASE}/projects/{project['id']}/documents",
        headers=auth(token),
        data={"doc_type": "mrv_record"},
        files={"file": ("mrv.pdf", io.BytesIO(b"data"), "application/pdf")},
    )
    assert r.status_code == 409


async def test_list_documents_success(client):
    token = await _register_and_verify(client)
    project = await _create_project(client, token)

    # Upload two documents
    for doc_type in ("registry_evidence", "land_ownership_proof"):
        await client.post(
            f"{BASE}/projects/{project['id']}/documents",
            headers=auth(token),
            data={"doc_type": doc_type},
            files={"file": (f"{doc_type}.pdf", io.BytesIO(b"content"), "application/pdf")},
        )

    r = await client.get(
        f"{BASE}/projects/{project['id']}/documents", headers=auth(token)
    )
    assert r.status_code == 200
    assert len(r.json()) == 2


async def test_list_documents_empty(client):
    token = await _register_and_verify(client)
    project = await _create_project(client, token)
    r = await client.get(
        f"{BASE}/projects/{project['id']}/documents", headers=auth(token)
    )
    assert r.status_code == 200
    assert r.json() == []


async def test_upload_document_cross_user_forbidden(client):
    token1 = await _register_and_verify(client, {"email": "d_a@example.com", "password": "pass12345"})
    token2 = await _register_and_verify(client, {"email": "d_b@example.com", "password": "pass12345"})
    project = await _create_project(client, token1)
    r = await client.post(
        f"{BASE}/projects/{project['id']}/documents",
        headers=auth(token2),
        data={"doc_type": "other"},
        files={"file": ("f.pdf", io.BytesIO(b"x"), "application/pdf")},
    )
    assert r.status_code == 404
