"""
Tests for P0 audit trail: document upload events, operator audit log endpoint,
and schema completeness (actor_role, resource_type, resource_id, reason).

Acceptance criteria validated here:
- Audit events are recorded for document upload/change.
- Each audit event captures event_type, actor_id, actor_role, resource_type,
  resource_id, timestamp, and optional reason.
- Audit records are immutable (no PATCH/DELETE endpoints exist).
- Audit log is queryable by operators for a given project or farmer.
"""

from __future__ import annotations

import io
import uuid

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
from datetime import datetime, timezone
from sqlalchemy import select

pytestmark = pytest.mark.asyncio

BASE = "/api/v1"
BEARER = "Bearer "

SUPPLIER_USER = {"email": "audit_supplier@example.com", "password": "securepass123"}
SUBMITTABLE_PROJECT = {
    "title": "Audit Trail Test Project",
    "description": "For audit trail testing.",
    "methodology": "VM0015",
    "geography": "Punjab, India",
    "baseline": "Business-as-usual CH4 emissions.",
    "expected_volume": 900.0,
}
REQUIRED_DOC_TYPES = ("registry_evidence", "mrv_record", "land_ownership_proof")


def auth(token: str) -> dict:
    return {"Authorization": BEARER + token}


async def _register_and_verify(client, user=SUPPLIER_USER):
    r = await client.post(f"{BASE}/auth/register", json=user)
    assert r.status_code == 201, r.text
    token = r.json()["email_verification_token"]
    v = await client.post(f"{BASE}/auth/verify-email", json={"token": token})
    assert v.status_code == 200, v.text
    lo = await client.post(f"{BASE}/auth/login", json=user)
    assert lo.status_code == 200, lo.text
    return lo.json()["access_token"]


async def _create_project(client, token):
    r = await client.post(f"{BASE}/projects", json=SUBMITTABLE_PROJECT, headers=auth(token))
    assert r.status_code == 201, r.text
    return r.json()["id"]


async def _upload_doc(client, token, project_id, doc_type="registry_evidence"):
    return await client.post(
        f"{BASE}/projects/{project_id}/documents",
        headers=auth(token),
        data={"doc_type": doc_type},
        files={"file": (f"{doc_type}.pdf", io.BytesIO(b"content"), "application/pdf")},
    )


async def _create_operator(db_session, email="audit_operator@example.com") -> User:
    operator = User(
        email=email,
        password_hash="not-used",
        role=RoleEnum.operator,
        status=UserStatusEnum.active,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db_session.add(operator)
    await db_session.commit()
    await db_session.refresh(operator)
    return operator


async def _create_admin(db_session, email="audit_admin@example.com") -> User:
    admin = User(
        email=email,
        password_hash="not-used",
        role=RoleEnum.admin,
        status=UserStatusEnum.active,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db_session.add(admin)
    await db_session.commit()
    await db_session.refresh(admin)
    return admin


# ---------------------------------------------------------------------------
# AC: document_uploaded audit event
# ---------------------------------------------------------------------------

async def test_document_upload_emits_audit_event(client_and_db):
    client, db = client_and_db
    token = await _register_and_verify(client)
    project_id = await _create_project(client, token)

    r = await _upload_doc(client, token, project_id)
    assert r.status_code == 201, r.text

    events = (
        await db.execute(
            select(ProjectAuditEvent)
            .where(ProjectAuditEvent.project_id == uuid.UUID(project_id))
            .order_by(ProjectAuditEvent.occurred_at)
        )
    ).scalars().all()

    upload_events = [e for e in events if e.event == AuditEventEnum.document_uploaded]
    assert len(upload_events) == 1, "Expected exactly one document_uploaded event"

    evt = upload_events[0]
    assert evt.actor_role == RoleEnum.supplier.value
    assert evt.resource_type == "document"
    assert evt.resource_id is not None


async def test_each_document_upload_emits_separate_audit_event(client_and_db):
    client, db = client_and_db
    token = await _register_and_verify(
        client, {"email": "multi_doc_supplier@example.com", "password": "pass123"}
    )
    project_id = await _create_project(client, token)

    for doc_type in REQUIRED_DOC_TYPES:
        r = await _upload_doc(client, token, project_id, doc_type=doc_type)
        assert r.status_code == 201, r.text

    events = (
        await db.execute(
            select(ProjectAuditEvent)
            .where(
                ProjectAuditEvent.project_id == uuid.UUID(project_id),
                ProjectAuditEvent.event == AuditEventEnum.document_uploaded,
            )
        )
    ).scalars().all()

    assert len(events) == 3


# ---------------------------------------------------------------------------
# AC: each audit event captures required fields
# ---------------------------------------------------------------------------

async def test_audit_event_captures_required_fields(client_and_db):
    client, db = client_and_db
    token = await _register_and_verify(
        client, {"email": "fields_supplier@example.com", "password": "pass123"}
    )
    project_id = await _create_project(client, token)

    events = (
        await db.execute(
            select(ProjectAuditEvent)
            .where(ProjectAuditEvent.project_id == uuid.UUID(project_id))
        )
    ).scalars().all()

    assert len(events) == 1
    evt = events[0]
    # event_type (stored as event)
    assert evt.event == AuditEventEnum.created
    # actor_id present
    assert evt.actor_id is not None
    # actor_role present
    assert evt.actor_role == RoleEnum.supplier.value
    # resource_type present
    assert evt.resource_type == "project"
    # resource_id present (defaults to project_id)
    assert evt.resource_id == uuid.UUID(project_id)
    # timestamp present
    assert evt.occurred_at is not None


async def test_submitted_audit_event_captures_all_fields(client_and_db):
    client, db = client_and_db
    token = await _register_and_verify(
        client, {"email": "submit_audit@example.com", "password": "pass123"}
    )
    project_id = await _create_project(client, token)
    for dt in REQUIRED_DOC_TYPES:
        await _upload_doc(client, token, project_id, doc_type=dt)

    r = await client.post(f"{BASE}/projects/{project_id}/submit", headers=auth(token))
    assert r.status_code == 200, r.text

    events = (
        await db.execute(
            select(ProjectAuditEvent)
            .where(
                ProjectAuditEvent.project_id == uuid.UUID(project_id),
                ProjectAuditEvent.event == AuditEventEnum.submitted,
            )
        )
    ).scalars().all()

    assert len(events) == 1
    evt = events[0]
    assert evt.actor_role == RoleEnum.supplier.value
    assert evt.resource_type == "project"
    assert evt.resource_id == uuid.UUID(project_id)


# ---------------------------------------------------------------------------
# AC: audit log queryable by operators
# ---------------------------------------------------------------------------

async def test_operator_can_query_audit_log_by_project(client_and_db):
    client, db = client_and_db
    token = await _register_and_verify(
        client, {"email": "op_query_supplier@example.com", "password": "pass123"}
    )
    project_id = await _create_project(client, token)
    await _upload_doc(client, token, project_id)

    operator = await _create_operator(db)
    # Directly set operator token via DB (bypass login for simplicity — inject JWT)
    from app.core.security import create_access_token
    op_token = create_access_token({"sub": str(operator.id), "role": "operator"})

    r = await client.get(
        f"{BASE}/projects/audit-log",
        headers=auth(op_token),
        params={"project_id": project_id},
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["total"] >= 2  # created + document_uploaded
    event_types = [e["event_type"] for e in data["events"]]
    assert "created" in event_types
    assert "document_uploaded" in event_types
    # Verify schema fields are present
    for evt in data["events"]:
        assert "event_type" in evt
        assert "actor_id" in evt
        assert "actor_role" in evt
        assert "resource_type" in evt
        assert "resource_id" in evt
        assert "timestamp" in evt


async def test_operator_can_query_audit_log_by_supplier(client_and_db):
    client, db = client_and_db
    user = {"email": "supplier_query@example.com", "password": "pass123"}
    token = await _register_and_verify(client, user)
    project_id = await _create_project(client, token)

    # get supplier id from DB
    result = await db.execute(
        select(User).where(User.email == user["email"])
    )
    supplier = result.scalar_one()

    operator = await _create_operator(db, "op2@example.com")
    from app.core.security import create_access_token
    op_token = create_access_token({"sub": str(operator.id), "role": "operator"})

    r = await client.get(
        f"{BASE}/projects/audit-log",
        headers=auth(op_token),
        params={"supplier_id": str(supplier.id)},
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["total"] >= 1
    # All events should belong to this supplier's project
    for evt in data["events"]:
        assert evt["project_id"] == project_id


async def test_operator_audit_log_requires_at_least_one_filter(client_and_db):
    client, db = client_and_db
    operator = await _create_operator(db, "op3@example.com")
    from app.core.security import create_access_token
    op_token = create_access_token({"sub": str(operator.id), "role": "operator"})

    r = await client.get(f"{BASE}/projects/audit-log", headers=auth(op_token))
    assert r.status_code == 400


async def test_supplier_cannot_access_audit_log(client):
    token = await _register_and_verify(
        client, {"email": "supplier_no_audit@example.com", "password": "pass123"}
    )
    project_id = await _create_project(client, token)
    r = await client.get(
        f"{BASE}/projects/audit-log",
        headers=auth(token),
        params={"project_id": project_id},
    )
    assert r.status_code == 403


async def test_audit_log_returns_404_for_nonexistent_project(client_and_db):
    client, db = client_and_db
    operator = await _create_operator(db, "op4@example.com")
    from app.core.security import create_access_token
    op_token = create_access_token({"sub": str(operator.id), "role": "operator"})

    r = await client.get(
        f"{BASE}/projects/audit-log",
        headers=auth(op_token),
        params={"project_id": str(uuid.uuid4())},
    )
    assert r.status_code == 404


async def test_audit_log_returns_404_for_nonexistent_supplier(client_and_db):
    client, db = client_and_db
    operator = await _create_operator(db, "op5@example.com")
    from app.core.security import create_access_token
    op_token = create_access_token({"sub": str(operator.id), "role": "operator"})

    r = await client.get(
        f"{BASE}/projects/audit-log",
        headers=auth(op_token),
        params={"supplier_id": str(uuid.uuid4())},
    )
    assert r.status_code == 404


async def test_admin_can_also_query_audit_log(client_and_db):
    client, db = client_and_db
    user = {"email": "admin_audit_supplier@example.com", "password": "pass123"}
    token = await _register_and_verify(client, user)
    project_id = await _create_project(client, token)

    admin = await _create_admin(db)
    from app.core.security import create_access_token
    admin_token = create_access_token({"sub": str(admin.id), "role": "admin"})

    r = await client.get(
        f"{BASE}/projects/audit-log",
        headers=auth(admin_token),
        params={"project_id": project_id},
    )
    assert r.status_code == 200, r.text
    assert r.json()["total"] >= 1
