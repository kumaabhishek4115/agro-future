"""
Tests for farmer-facing submission receipts and project intake timeline history.
"""

from __future__ import annotations

import io
import json
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from app.db.models import (
    AuditEventEnum,
    Project,
    ProjectAuditEvent,
    ProjectStatusEnum,
    RoleEnum,
    User,
    UserStatusEnum,
)
from sqlalchemy import select

pytestmark = pytest.mark.asyncio

BASE = "/api/v1"
BEARER = "Bearer "

VALID_USER = {"email": "farmer_timeline@example.com", "password": "securepass123"}

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


def snapshot_for(project: Project) -> str:
    return json.dumps(
        {
            "title": project.title,
            "description": project.description,
            "methodology": project.methodology,
            "geography": project.geography,
            "baseline": project.baseline,
            "expected_volume": project.expected_volume,
            "status": project.status.value,
            "review_reason": project.review_reason,
        }
    )


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
    r = await client.post(f"{BASE}/projects", json=SUBMITTABLE_PROJECT, headers=auth(token))
    assert r.status_code == 201, r.text
    project_id = r.json()["id"]
    await _upload_required_documents(client, token, project_id)
    r2 = await client.post(f"{BASE}/projects/{project_id}/submit", headers=auth(token))
    assert r2.status_code == 200, r2.text
    return r2.json()


async def _get_user_by_email(db_session, email: str) -> User:
    result = await db_session.execute(select(User).where(User.email == email))
    return result.scalar_one()


async def _create_operator(db_session) -> User:
    operator = User(
        email="operator@example.com",
        password_hash="not-used-in-tests",
        role=RoleEnum.admin,
        status=UserStatusEnum.active,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db_session.add(operator)
    await db_session.commit()
    await db_session.refresh(operator)
    return operator


async def _append_status_event(
    db_session,
    project_id: str,
    *,
    status: ProjectStatusEnum,
    event: AuditEventEnum,
    actor_id: uuid.UUID | None,
    occurred_at: datetime,
    reason: str | None = None,
):
    result = await db_session.execute(select(Project).where(Project.id == uuid.UUID(project_id)))
    project = result.scalar_one()
    project.status = status
    project.review_reason = reason
    project.updated_at = occurred_at
    if status == ProjectStatusEnum.submitted:
        project.submitted_at = occurred_at
    db_session.add(
        ProjectAuditEvent(
            project_id=project.id,
            actor_id=actor_id,
            event=event,
            snapshot_json=snapshot_for(project),
            occurred_at=occurred_at,
        )
    )
    await db_session.commit()


async def test_submit_response_includes_submission_receipt(client):
    token = await _register_and_verify(client)
    submitted = await _create_and_submit_project(client, token)

    assert submitted["status"] == "submitted"
    assert submitted["submission_receipt"]["project_id"] == submitted["id"]
    assert submitted["submission_receipt"]["current_status"] == "submitted"
    assert submitted["submission_receipt"]["submitted_at"] == submitted["submitted_at"]
    assert "received" in submitted["submission_receipt"]["message"].lower()


async def test_timeline_returns_chronological_status_history_with_reasons(client_and_db):
    client, db = client_and_db
    token = await _register_and_verify(client)
    submitted = await _create_and_submit_project(client, token)
    project_id = submitted["id"]
    farmer = await _get_user_by_email(db, VALID_USER["email"])
    operator = await _create_operator(db)
    base_time = datetime.now(timezone.utc)

    await _append_status_event(
        db,
        project_id,
        status=ProjectStatusEnum.in_review,
        event=AuditEventEnum.in_review,
        actor_id=operator.id,
        occurred_at=base_time + timedelta(minutes=1),
    )
    await _append_status_event(
        db,
        project_id,
        status=ProjectStatusEnum.needs_info,
        event=AuditEventEnum.needs_info,
        actor_id=operator.id,
        occurred_at=base_time + timedelta(minutes=2),
        reason="Please provide a clearer baseline dataset.",
    )

    await _append_status_event(
        db,
        project_id,
        status=ProjectStatusEnum.submitted,
        event=AuditEventEnum.resubmitted,
        actor_id=farmer.id,
        occurred_at=base_time + timedelta(minutes=3),
    )

    await _append_status_event(
        db,
        project_id,
        status=ProjectStatusEnum.approved,
        event=AuditEventEnum.approved,
        actor_id=operator.id,
        occurred_at=base_time + timedelta(minutes=4),
    )

    timeline_response = await client.get(f"{BASE}/projects/{project_id}/timeline", headers=auth(token))
    assert timeline_response.status_code == 200, timeline_response.text
    data = timeline_response.json()

    assert data["current_status"] == "approved"
    assert data["submission_receipt"]["project_id"] == project_id

    statuses = [entry["status"] for entry in data["timeline"]]
    assert statuses == ["draft", "submitted", "in_review", "needs_info", "submitted", "approved"]

    timestamps = [entry["timestamp"] for entry in data["timeline"]]
    assert timestamps == sorted(timestamps)

    assert data["timeline"][0]["actor_role"] == farmer.role.value
    assert data["timeline"][1]["actor_role"] == farmer.role.value
    assert data["timeline"][2]["actor_role"] == operator.role.value
    assert data["timeline"][3]["reason"] == "Please provide a clearer baseline dataset."
    assert data["timeline"][5]["reason"] is None


async def test_timeline_updates_on_follow_up_reads_and_shows_rejected_reason(client_and_db):
    client, db = client_and_db
    token = await _register_and_verify(client, {"email": "farmer_timeline_2@example.com", "password": "securepass123"})
    submitted = await _create_and_submit_project(client, token)
    project_id = submitted["id"]
    operator = await _create_operator(db)
    base_time = datetime.now(timezone.utc)

    first = await client.get(f"{BASE}/projects/{project_id}/timeline", headers=auth(token))
    assert first.status_code == 200, first.text
    assert [entry["status"] for entry in first.json()["timeline"]] == ["draft", "submitted"]

    await _append_status_event(
        db,
        project_id,
        status=ProjectStatusEnum.in_review,
        event=AuditEventEnum.in_review,
        actor_id=operator.id,
        occurred_at=base_time + timedelta(minutes=1),
    )
    await _append_status_event(
        db,
        project_id,
        status=ProjectStatusEnum.rejected,
        event=AuditEventEnum.rejected,
        actor_id=operator.id,
        occurred_at=base_time + timedelta(minutes=2),
        reason="Registry evidence does not meet validation requirements.",
    )

    second = await client.get(f"{BASE}/projects/{project_id}/timeline", headers=auth(token))
    assert second.status_code == 200, second.text
    data = second.json()
    assert data["current_status"] == "rejected"
    assert [entry["status"] for entry in data["timeline"]] == ["draft", "submitted", "in_review", "rejected"]
    assert data["timeline"][-1]["reason"] == "Registry evidence does not meet validation requirements."


async def test_timeline_gracefully_handles_project_without_audit_history(client_and_db):
    client, db = client_and_db
    token = await _register_and_verify(client, {"email": "farmer_timeline_3@example.com", "password": "securepass123"})
    farmer = await _get_user_by_email(db, "farmer_timeline_3@example.com")
    now = datetime.now(timezone.utc)
    project = Project(
        supplier_id=farmer.id,
        title="No-history submitted project",
        description="Imported project",
        methodology="VM0015",
        geography="Punjab, India",
        baseline="Existing baseline",
        expected_volume=900.0,
        status=ProjectStatusEnum.submitted,
        submitted_at=now,
        created_at=now - timedelta(minutes=5),
        updated_at=now,
    )
    db.add(project)
    await db.commit()
    await db.refresh(project)

    response = await client.get(f"{BASE}/projects/{project.id}/timeline", headers=auth(token))
    assert response.status_code == 200, response.text
    data = response.json()

    assert data["current_status"] == "submitted"
    assert data["submission_receipt"]["project_id"] == str(project.id)
    assert len(data["timeline"]) == 1
    assert data["timeline"][0]["status"] == "submitted"
    assert data["timeline"][0]["actor_role"] == farmer.role.value
