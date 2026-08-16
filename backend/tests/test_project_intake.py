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

# A project with all submission-required fields populated (used by tests that need
# to actually submit a project: methodology, geography, baseline, expected_volume).
SUBMITTABLE_PROJECT = {
    **VALID_PROJECT,
    "baseline": "Business-as-usual CH4 emissions from flooded paddy.",
    "expected_volume": 1200.0,
}

BEARER = "Bearer "
REQUIRED_DOC_TYPES = (
    "registry_evidence",
    "mrv_record",
    "land_ownership_proof",
)


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


async def _create_submittable_project(client, token, data=None):
    """Create a project that has all fields required for submission."""
    data = data or SUBMITTABLE_PROJECT
    r = await client.post(f"{BASE}/projects", json=data, headers=auth(token))
    assert r.status_code == 201, r.text
    return r.json()


async def _upload_document(
    client,
    token,
    project_id,
    *,
    doc_type="registry_evidence",
    filename=None,
    content=b"content",
    mime_type="application/pdf",
):
    filename = filename or f"{doc_type}.pdf"
    return await client.post(
        f"{BASE}/projects/{project_id}/documents",
        headers=auth(token),
        data={"doc_type": doc_type},
        files={"file": (filename, io.BytesIO(content), mime_type)},
    )


async def _upload_required_documents(client, token, project_id):
    for doc_type in REQUIRED_DOC_TYPES:
        response = await _upload_document(client, token, project_id, doc_type=doc_type)
        assert response.status_code == 201, response.text


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
    project = await _create_submittable_project(client, token)
    await _upload_required_documents(client, token, project["id"])
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
    project = await _create_submittable_project(client, token)
    await _upload_required_documents(client, token, project["id"])
    r = await client.post(
        f"{BASE}/projects/{project['id']}/submit", headers=auth(token)
    )
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "submitted"
    assert data["submitted_at"] is not None


async def test_submit_already_submitted(client):
    token = await _register_and_verify(client)
    project = await _create_submittable_project(client, token)
    await _upload_required_documents(client, token, project["id"])
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
    r = await _upload_document(
        client,
        token,
        project["id"],
        doc_type="registry_evidence",
        filename="evidence.pdf",
        content=file_content,
    )
    assert r.status_code == 201
    data = r.json()
    assert data["doc_type"] == "registry_evidence"
    assert data["filename"] == "evidence.pdf"
    assert len(data["checksum"]) == 64  # SHA-256 hex
    assert data["project_id"] == project["id"]
    assert data["storage_uri"].endswith("/registry_evidence/evidence.pdf")


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


async def test_upload_document_invalid_mime_type(client):
    token = await _register_and_verify(client)
    project = await _create_project(client, token)
    r = await _upload_document(
        client,
        token,
        project["id"],
        doc_type="registry_evidence",
        filename="notes.txt",
        content=b"plain text",
        mime_type="text/plain",
    )
    assert r.status_code == 415
    assert "Unsupported file type" in r.json()["detail"]


async def test_upload_document_too_large(client, monkeypatch):
    from app.routers import project as project_router

    monkeypatch.setattr(project_router, "MAX_FILE_BYTES", 5)
    token = await _register_and_verify(client)
    project = await _create_project(client, token)
    r = await _upload_document(
        client,
        token,
        project["id"],
        doc_type="registry_evidence",
        content=b"123456",
    )
    assert r.status_code == 413
    assert "maximum allowed size" in r.json()["detail"]


async def test_upload_document_to_submitted_project_rejected(client):
    """Documents cannot be uploaded to an already-submitted project."""
    token = await _register_and_verify(client)
    project = await _create_submittable_project(client, token)
    await _upload_required_documents(client, token, project["id"])
    await client.post(f"{BASE}/projects/{project['id']}/submit", headers=auth(token))
    r = await _upload_document(
        client,
        token,
        project["id"],
        doc_type="mrv_record",
        filename="mrv.pdf",
        content=b"data",
    )
    assert r.status_code == 409


async def test_list_documents_success(client):
    token = await _register_and_verify(client)
    project = await _create_project(client, token)

    # Upload two documents
    for doc_type in ("registry_evidence", "land_ownership_proof"):
        response = await _upload_document(client, token, project["id"], doc_type=doc_type)
        assert response.status_code == 201, response.text

    r = await client.get(
        f"{BASE}/projects/{project['id']}/documents", headers=auth(token)
    )
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 2
    assert [doc["doc_type"] for doc in data] == [
        "registry_evidence",
        "land_ownership_proof",
    ]
    assert all(doc["uploaded_at"] for doc in data)


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
    r = await _upload_document(
        client,
        token2,
        project["id"],
        doc_type="registry_evidence",
        filename="f.pdf",
        content=b"x",
    )
    assert r.status_code == 404


async def test_list_documents_cross_user_forbidden(client):
    token1 = await _register_and_verify(client, {"email": "d_c@example.com", "password": "pass12345"})
    token2 = await _register_and_verify(client, {"email": "d_d@example.com", "password": "pass12345"})
    project = await _create_project(client, token1)
    r = await client.get(f"{BASE}/projects/{project['id']}/documents", headers=auth(token2))
    assert r.status_code == 404


# ===========================================================================
# Acceptance Criteria tests – Issue #17: Project draft creation and state
# management (Epic 2, §5.1)
# ===========================================================================

# ---------------------------------------------------------------------------
# AC1 – Farmers can save a draft without completing all required fields
# ---------------------------------------------------------------------------

async def test_ac1_create_draft_without_optional_fields(client):
    """Draft can be saved with only the minimum required fields; optional fields
    (description, baseline, expected_volume) may be absent."""
    token = await _register_and_verify(client, {"email": "ac1_farmer@example.com", "password": "pass12345"})
    minimal = {
        "title": "Minimal Draft Project",
        "methodology": "VM0015",
        "geography": "Kerala, India",
    }
    r = await client.post(f"{BASE}/projects", json=minimal, headers=auth(token))
    assert r.status_code == 201
    data = r.json()
    assert data["status"] == "draft"
    assert data["description"] is None
    assert data["baseline"] is None
    assert data["expected_volume"] is None


async def test_ac1_create_draft_with_all_fields(client):
    """Draft can also be saved when all fields including baseline and
    expected_volume are provided."""
    token = await _register_and_verify(client, {"email": "ac1b_farmer@example.com", "password": "pass12345"})
    full = {
        "title": "Full Draft Project",
        "description": "Detailed description.",
        "methodology": "VM0015",
        "geography": "Punjab, India",
        "baseline": "Business-as-usual CH4 from flooded paddy.",
        "expected_volume": 1500.0,
    }
    r = await client.post(f"{BASE}/projects", json=full, headers=auth(token))
    assert r.status_code == 201
    data = r.json()
    assert data["status"] == "draft"
    assert data["baseline"] == full["baseline"]
    assert data["expected_volume"] == full["expected_volume"]


# ---------------------------------------------------------------------------
# AC2 – Farmers can resume an existing draft from their project list
# ---------------------------------------------------------------------------

async def test_ac2_resume_draft_from_list(client):
    """A draft project saved partially can be fetched from the project list
    and then updated to add missing fields – simulating 'resume draft'."""
    token = await _register_and_verify(client, {"email": "ac2_farmer@example.com", "password": "pass12345"})
    # Step 1: create a minimal draft
    partial = {
        "title": "Resumable Draft",
        "methodology": "AMS-III.AU",
        "geography": "Tamil Nadu, India",
    }
    r_create = await client.post(f"{BASE}/projects", json=partial, headers=auth(token))
    assert r_create.status_code == 201
    project_id = r_create.json()["id"]

    # Step 2: list projects – the draft is visible
    r_list = await client.get(f"{BASE}/projects", headers=auth(token))
    assert r_list.status_code == 200
    ids = [p["id"] for p in r_list.json()]
    assert project_id in ids

    # Step 3: fetch the individual draft
    r_get = await client.get(f"{BASE}/projects/{project_id}", headers=auth(token))
    assert r_get.status_code == 200
    assert r_get.json()["status"] == "draft"

    # Step 4: resume – patch in the remaining fields
    r_patch = await client.patch(
        f"{BASE}/projects/{project_id}",
        json={"baseline": "BAU emissions baseline.", "expected_volume": 800.0},
        headers=auth(token),
    )
    assert r_patch.status_code == 200
    updated = r_patch.json()
    assert updated["baseline"] == "BAU emissions baseline."
    assert updated["expected_volume"] == 800.0
    # Fields from original save are preserved
    assert updated["methodology"] == "AMS-III.AU"


# ---------------------------------------------------------------------------
# AC3 – Submission blocked with clear validation errors until all required
#        fields are complete
# ---------------------------------------------------------------------------

async def test_ac3_submit_blocked_missing_baseline(client):
    """Submitting a draft without 'baseline' returns 422 with an error message
    naming the missing field."""
    token = await _register_and_verify(client, {"email": "ac3a_farmer@example.com", "password": "pass12345"})
    project = await _create_project(client, token)
    # VALID_PROJECT has no baseline / expected_volume
    r = await client.post(f"{BASE}/projects/{project['id']}/submit", headers=auth(token))
    assert r.status_code == 422
    detail = r.json()["detail"]
    assert "baseline" in detail
    assert "expected_volume" in detail


async def test_ac3_submit_blocked_missing_expected_volume(client):
    """Submitting with baseline set but expected_volume still missing returns 422."""
    token = await _register_and_verify(client, {"email": "ac3b_farmer@example.com", "password": "pass12345"})
    project = await _create_project(client, token)
    await client.patch(
        f"{BASE}/projects/{project['id']}",
        json={"baseline": "Some baseline description."},
        headers=auth(token),
    )
    r = await client.post(f"{BASE}/projects/{project['id']}/submit", headers=auth(token))
    assert r.status_code == 422
    assert "expected_volume" in r.json()["detail"]


async def test_ac3_submit_succeeds_when_all_required_fields_present(client):
    """Submission succeeds once methodology, geography, baseline and
    expected_volume are all populated."""
    token = await _register_and_verify(client, {"email": "ac3c_farmer@example.com", "password": "pass12345"})
    project = await _create_project(client, token)
    await client.patch(
        f"{BASE}/projects/{project['id']}",
        json={"baseline": "BAU baseline.", "expected_volume": 2000.0},
        headers=auth(token),
    )
    await _upload_required_documents(client, token, project["id"])
    r = await client.post(f"{BASE}/projects/{project['id']}/submit", headers=auth(token))
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "submitted"


async def test_submit_project_blocked_when_required_documents_missing(client):
    token = await _register_and_verify(client, {"email": "ac3d_farmer@example.com", "password": "pass12345"})
    project = await _create_submittable_project(client, token)
    r = await client.post(f"{BASE}/projects/{project['id']}/submit", headers=auth(token))
    assert r.status_code == 422
    detail = r.json()["detail"]
    assert "required document types are missing" in detail
    for doc_type in REQUIRED_DOC_TYPES:
        assert doc_type in detail


async def test_submit_project_allows_optional_document_types_in_addition_to_required_ones(client):
    token = await _register_and_verify(client, {"email": "ac3e_farmer@example.com", "password": "pass12345"})
    project = await _create_submittable_project(client, token)
    await _upload_required_documents(client, token, project["id"])
    extra = await _upload_document(
        client,
        token,
        project["id"],
        doc_type="other",
        filename="extra.pdf",
        content=b"extra",
    )
    assert extra.status_code == 201
    r = await client.post(f"{BASE}/projects/{project['id']}/submit", headers=auth(token))
    assert r.status_code == 200


# ---------------------------------------------------------------------------
# AC4 – Project state transitions are visible in the farmer portal
# ---------------------------------------------------------------------------

async def test_ac4_draft_status_visible_on_create(client):
    """Newly created project is in 'draft' state and that is visible to
    the farmer in both list and single-project responses."""
    token = await _register_and_verify(client, {"email": "ac4a_farmer@example.com", "password": "pass12345"})
    project = await _create_project(client, token)
    assert project["status"] == "draft"

    r_list = await client.get(f"{BASE}/projects", headers=auth(token))
    draft_project = next(p for p in r_list.json() if p["id"] == project["id"])
    assert draft_project["status"] == "draft"


async def test_ac4_submitted_status_visible_after_submit(client):
    """After submission the project status is 'submitted' in both list and
    single-project responses."""
    token = await _register_and_verify(client, {"email": "ac4b_farmer@example.com", "password": "pass12345"})
    # Create a fully-filled project so submission is not blocked
    full = {**VALID_PROJECT, "baseline": "BAU baseline.", "expected_volume": 500.0}
    r_create = await client.post(f"{BASE}/projects", json=full, headers=auth(token))
    assert r_create.status_code == 201
    project_id = r_create.json()["id"]
    await _upload_required_documents(client, token, project_id)

    await client.post(f"{BASE}/projects/{project_id}/submit", headers=auth(token))

    r_get = await client.get(f"{BASE}/projects/{project_id}", headers=auth(token))
    assert r_get.json()["status"] == "submitted"

    r_list = await client.get(f"{BASE}/projects", headers=auth(token))
    submitted = next(p for p in r_list.json() if p["id"] == project_id)
    assert submitted["status"] == "submitted"


async def test_ac4_all_status_enum_values_represented(client):
    """Verify that the API response status field can represent all six
    lifecycle states defined in the issue: draft, submitted, in_review,
    needs_info, approved, rejected."""
    from app.models.project import ProjectStatus
    expected_states = {"draft", "submitted", "in_review", "needs_info", "approved", "rejected"}
    actual_states = {s.value for s in ProjectStatus}
    assert expected_states == actual_states


# ---------------------------------------------------------------------------
# AC5 – Required project fields: methodology, geography, baseline,
#        expected_volume, and project metadata (title)
# ---------------------------------------------------------------------------

async def test_ac5_create_requires_title(client):
    token = await _register_and_verify(client, {"email": "ac5a_farmer@example.com", "password": "pass12345"})
    no_title = {k: v for k, v in VALID_PROJECT.items() if k != "title"}
    r = await client.post(f"{BASE}/projects", json=no_title, headers=auth(token))
    assert r.status_code == 422


async def test_ac5_create_requires_methodology(client):
    token = await _register_and_verify(client, {"email": "ac5b_farmer@example.com", "password": "pass12345"})
    no_methodology = {k: v for k, v in VALID_PROJECT.items() if k != "methodology"}
    r = await client.post(f"{BASE}/projects", json=no_methodology, headers=auth(token))
    assert r.status_code == 422


async def test_ac5_create_requires_geography(client):
    token = await _register_and_verify(client, {"email": "ac5c_farmer@example.com", "password": "pass12345"})
    no_geography = {k: v for k, v in VALID_PROJECT.items() if k != "geography"}
    r = await client.post(f"{BASE}/projects", json=no_geography, headers=auth(token))
    assert r.status_code == 422


async def test_ac5_expected_volume_must_be_positive(client):
    """expected_volume <= 0 is rejected at the schema layer."""
    token = await _register_and_verify(client, {"email": "ac5d_farmer@example.com", "password": "pass12345"})
    bad = {**VALID_PROJECT, "baseline": "BAU", "expected_volume": -50.0}
    r = await client.post(f"{BASE}/projects", json=bad, headers=auth(token))
    assert r.status_code == 422


async def test_ac5_project_response_includes_all_required_fields(client):
    """Project response exposes methodology, geography, baseline,
    expected_volume and project metadata (id, title, status, timestamps)."""
    token = await _register_and_verify(client, {"email": "ac5e_farmer@example.com", "password": "pass12345"})
    full = {**VALID_PROJECT, "baseline": "BAU baseline.", "expected_volume": 1000.0}
    r = await client.post(f"{BASE}/projects", json=full, headers=auth(token))
    assert r.status_code == 201
    data = r.json()
    for field in ("id", "title", "methodology", "geography", "baseline", "expected_volume",
                  "status", "created_at", "updated_at"):
        assert field in data, f"Missing field in response: {field}"


# ---------------------------------------------------------------------------
# AC6 – Submitting records a timestamp and moves state to 'submitted'
# ---------------------------------------------------------------------------

async def test_ac6_submit_records_submitted_at_timestamp(client):
    """submitted_at must be a non-null ISO-8601 datetime after submission."""
    token = await _register_and_verify(client, {"email": "ac6_farmer@example.com", "password": "pass12345"})
    full = {**VALID_PROJECT, "baseline": "BAU baseline.", "expected_volume": 750.0}
    r_create = await client.post(f"{BASE}/projects", json=full, headers=auth(token))
    assert r_create.status_code == 201
    assert r_create.json()["submitted_at"] is None

    project_id = r_create.json()["id"]
    await _upload_required_documents(client, token, project_id)
    r_submit = await client.post(f"{BASE}/projects/{project_id}/submit", headers=auth(token))
    assert r_submit.status_code == 200
    data = r_submit.json()
    assert data["status"] == "submitted"
    assert data["submitted_at"] is not None
    # submitted_at must be parseable as an ISO-8601 string
    from datetime import datetime
    datetime.fromisoformat(data["submitted_at"].replace("Z", "+00:00"))


async def test_ac6_submitted_at_null_for_draft(client):
    """submitted_at is None on a draft project."""
    token = await _register_and_verify(client, {"email": "ac6b_farmer@example.com", "password": "pass12345"})
    project = await _create_project(client, token)
    assert project["submitted_at"] is None
