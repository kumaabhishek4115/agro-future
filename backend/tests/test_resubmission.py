"""
Tests for Epic 3 – Needs-info resolution and resubmission flow.

Covers:
  PATCH  /api/v1/projects/{project_id}          – edit while in needs_info
  POST   /api/v1/projects/{project_id}/documents – upload while in needs_info
  POST   /api/v1/projects/{project_id}/resubmit  – resubmit a needs_info project

TRD §5.2 acceptance criteria:
  - needs_info/rejected decisions display the required reason text.
  - Farmers can edit specific fields while in needs_info.
  - Farmers can upload documents while in needs_info.
  - Resubmission transitions back to submitted state.
  - All prior versions are preserved in the audit log.
  - Farmer cannot resubmit from approved/rejected/in_review state.
"""

from __future__ import annotations

import io
import uuid

import pytest
from app.db.models import Project, ProjectStatusEnum
from sqlalchemy import select

pytestmark = pytest.mark.asyncio

BASE = "/api/v1"
BEARER = "Bearer "

VALID_USER = {"email": "farmer_e3@example.com", "password": "securepass123"}

SUBMITTABLE_PROJECT = {
    "title": "Rice Field Carbon Sequestration",
    "description": "Improved paddy management reducing CH4 emissions.",
    "methodology": "VM0015",
    "geography": "Punjab, India",
    "baseline": "Business-as-usual CH4 emissions from flooded paddy.",
    "expected_volume": 1200.0,
}

REQUIRED_DOC_TYPES = (
    "registry_evidence",
    "mrv_record",
    "land_ownership_proof",
)


def auth(token: str) -> dict:
    return {"Authorization": BEARER + token}


async def _register_and_verify(client, user=None):
    user = user or VALID_USER
    r = await client.post(f"{BASE}/auth/register", json=user)
    assert r.status_code == 201, r.text
    token = r.json()["email_verification_token"]
    v = await client.post(f"{BASE}/auth/verify-email", json={"token": token})
    assert v.status_code == 200, v.text
    lo = await client.post(f"{BASE}/auth/login", json=user)
    assert lo.status_code == 200, lo.text
    return lo.json()["access_token"]


async def _upload_document(client, token, project_id, *, doc_type="registry_evidence"):
    filename = f"{doc_type}.pdf"
    return await client.post(
        f"{BASE}/projects/{project_id}/documents",
        headers=auth(token),
        data={"doc_type": doc_type},
        files={"file": (filename, io.BytesIO(b"content"), "application/pdf")},
    )


async def _upload_required_documents(client, token, project_id):
    for doc_type in REQUIRED_DOC_TYPES:
        r = await _upload_document(client, token, project_id, doc_type=doc_type)
        assert r.status_code == 201, r.text


async def _create_and_submit_project(client, token):
    """Create, upload required docs, and submit a project; return the project dict."""
    r = await client.post(f"{BASE}/projects", json=SUBMITTABLE_PROJECT, headers=auth(token))
    assert r.status_code == 201, r.text
    project_id = r.json()["id"]
    await _upload_required_documents(client, token, project_id)
    r2 = await client.post(f"{BASE}/projects/{project_id}/submit", headers=auth(token))
    assert r2.status_code == 200, r2.text
    return r2.json()


async def _force_project_status(db_session, project_id: str, status: ProjectStatusEnum, reason: str | None = None):
    """Directly set project status (simulates reviewer action)."""
    result = await db_session.execute(
        select(Project).where(Project.id == uuid.UUID(project_id))
    )
    project = result.scalar_one()
    project.status = status
    if reason is not None:
        project.review_reason = reason
    await db_session.commit()
    await db_session.refresh(project)
    return project


# ---------------------------------------------------------------------------
# AC1 – review_reason is visible in project response when status is needs_info
# ---------------------------------------------------------------------------

async def test_review_reason_visible_when_needs_info(client_and_db):
    client, db = client_and_db
    token = await _register_and_verify(client)
    submitted = await _create_and_submit_project(client, token)
    project_id = submitted["id"]

    await _force_project_status(db, project_id, ProjectStatusEnum.needs_info, reason="Baseline data is incomplete.")

    r = await client.get(f"{BASE}/projects/{project_id}", headers=auth(token))
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "needs_info"
    assert data["review_reason"] == "Baseline data is incomplete."


async def test_review_reason_none_for_draft_project(client):
    token = await _register_and_verify(client)
    r = await client.post(f"{BASE}/projects", json=SUBMITTABLE_PROJECT, headers=auth(token))
    assert r.status_code == 201
    assert r.json()["review_reason"] is None


# ---------------------------------------------------------------------------
# AC2 – Farmers can edit fields in needs_info state
# ---------------------------------------------------------------------------

async def test_update_project_allowed_in_needs_info(client_and_db):
    client, db = client_and_db
    token = await _register_and_verify(client)
    submitted = await _create_and_submit_project(client, token)
    project_id = submitted["id"]

    await _force_project_status(db, project_id, ProjectStatusEnum.needs_info, reason="Please clarify baseline.")

    r = await client.patch(
        f"{BASE}/projects/{project_id}",
        json={"baseline": "Updated baseline methodology."},
        headers=auth(token),
    )
    assert r.status_code == 200
    assert r.json()["baseline"] == "Updated baseline methodology."
    assert r.json()["status"] == "needs_info"


async def test_update_project_rejected_in_submitted_state(client):
    token = await _register_and_verify(client)
    submitted = await _create_and_submit_project(client, token)
    project_id = submitted["id"]

    r = await client.patch(
        f"{BASE}/projects/{project_id}",
        json={"baseline": "New baseline."},
        headers=auth(token),
    )
    assert r.status_code == 409


async def test_update_project_rejected_in_approved_state(client_and_db):
    client, db = client_and_db
    token = await _register_and_verify(client)
    submitted = await _create_and_submit_project(client, token)
    project_id = submitted["id"]

    await _force_project_status(db, project_id, ProjectStatusEnum.approved)

    r = await client.patch(
        f"{BASE}/projects/{project_id}",
        json={"baseline": "New baseline."},
        headers=auth(token),
    )
    assert r.status_code == 409


# ---------------------------------------------------------------------------
# AC3 – Farmers can upload replacement documents in needs_info state
# ---------------------------------------------------------------------------

async def test_upload_document_allowed_in_needs_info(client_and_db):
    client, db = client_and_db
    token = await _register_and_verify(client)
    submitted = await _create_and_submit_project(client, token)
    project_id = submitted["id"]

    await _force_project_status(db, project_id, ProjectStatusEnum.needs_info, reason="Provide updated MRV record.")

    r = await _upload_document(client, token, project_id, doc_type="mrv_record")
    assert r.status_code == 201
    assert r.json()["doc_type"] == "mrv_record"


async def test_upload_document_rejected_in_submitted_state(client):
    token = await _register_and_verify(client)
    submitted = await _create_and_submit_project(client, token)
    project_id = submitted["id"]

    r = await _upload_document(client, token, project_id, doc_type="other")
    assert r.status_code == 409


# ---------------------------------------------------------------------------
# AC4 – Resubmission transitions project back to submitted
# ---------------------------------------------------------------------------

async def test_resubmit_project_success(client_and_db):
    client, db = client_and_db
    token = await _register_and_verify(client)
    submitted = await _create_and_submit_project(client, token)
    project_id = submitted["id"]

    await _force_project_status(db, project_id, ProjectStatusEnum.needs_info, reason="Needs more detail.")

    r = await client.post(f"{BASE}/projects/{project_id}/resubmit", headers=auth(token))
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "submitted"
    # review_reason is cleared on resubmission
    assert data["review_reason"] is None


async def test_resubmit_clears_review_reason(client_and_db):
    client, db = client_and_db
    token = await _register_and_verify(client)
    submitted = await _create_and_submit_project(client, token)
    project_id = submitted["id"]

    await _force_project_status(db, project_id, ProjectStatusEnum.needs_info, reason="Need more info.")

    r = await client.post(f"{BASE}/projects/{project_id}/resubmit", headers=auth(token))
    assert r.status_code == 200
    assert r.json()["review_reason"] is None


# ---------------------------------------------------------------------------
# AC5 – Farmer cannot resubmit from invalid states
# ---------------------------------------------------------------------------

async def test_resubmit_rejected_from_draft(client):
    token = await _register_and_verify(client)
    r = await client.post(f"{BASE}/projects", json=SUBMITTABLE_PROJECT, headers=auth(token))
    project_id = r.json()["id"]

    r2 = await client.post(f"{BASE}/projects/{project_id}/resubmit", headers=auth(token))
    assert r2.status_code == 409
    assert "needs_info" in r2.json()["detail"]


async def test_resubmit_rejected_from_submitted(client):
    token = await _register_and_verify(client)
    submitted = await _create_and_submit_project(client, token)
    project_id = submitted["id"]

    r = await client.post(f"{BASE}/projects/{project_id}/resubmit", headers=auth(token))
    assert r.status_code == 409


async def test_resubmit_rejected_from_approved(client_and_db):
    client, db = client_and_db
    token = await _register_and_verify(client)
    submitted = await _create_and_submit_project(client, token)
    project_id = submitted["id"]

    await _force_project_status(db, project_id, ProjectStatusEnum.approved)

    r = await client.post(f"{BASE}/projects/{project_id}/resubmit", headers=auth(token))
    assert r.status_code == 409


async def test_resubmit_rejected_from_rejected(client_and_db):
    client, db = client_and_db
    token = await _register_and_verify(client)
    submitted = await _create_and_submit_project(client, token)
    project_id = submitted["id"]

    await _force_project_status(db, project_id, ProjectStatusEnum.rejected)

    r = await client.post(f"{BASE}/projects/{project_id}/resubmit", headers=auth(token))
    assert r.status_code == 409


async def test_resubmit_rejected_from_in_review(client_and_db):
    client, db = client_and_db
    token = await _register_and_verify(client)
    submitted = await _create_and_submit_project(client, token)
    project_id = submitted["id"]

    await _force_project_status(db, project_id, ProjectStatusEnum.in_review)

    r = await client.post(f"{BASE}/projects/{project_id}/resubmit", headers=auth(token))
    assert r.status_code == 409


# ---------------------------------------------------------------------------
# Resubmit fails if required documents are missing
# ---------------------------------------------------------------------------

async def test_resubmit_fails_without_required_documents(client_and_db):
    """A project with only one required doc cannot be resubmitted."""
    client, db = client_and_db
    token = await _register_and_verify(client)
    r = await client.post(f"{BASE}/projects", json=SUBMITTABLE_PROJECT, headers=auth(token))
    project_id = r.json()["id"]

    # Only upload one doc, then force needs_info via DB
    await _upload_document(client, token, project_id, doc_type="registry_evidence")

    await _force_project_status(db, project_id, ProjectStatusEnum.needs_info, reason="Missing docs.")

    r2 = await client.post(f"{BASE}/projects/{project_id}/resubmit", headers=auth(token))
    assert r2.status_code == 422
    assert "mrv_record" in r2.json()["detail"] or "land_ownership_proof" in r2.json()["detail"]


# ---------------------------------------------------------------------------
# Resubmit unauthenticated returns 403
# ---------------------------------------------------------------------------

async def test_resubmit_unauthenticated(client_and_db):
    client, db = client_and_db
    token = await _register_and_verify(client)
    submitted = await _create_and_submit_project(client, token)
    project_id = submitted["id"]
    await _force_project_status(db, project_id, ProjectStatusEnum.needs_info)

    r = await client.post(f"{BASE}/projects/{project_id}/resubmit")
    assert r.status_code == 403
