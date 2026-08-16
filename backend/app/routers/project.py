"""
Project intake endpoints (Epic 2 & 3).

POST   /api/v1/projects                          – create a draft project
GET    /api/v1/projects                          – list my projects
GET    /api/v1/projects/{project_id}             – get a project
PATCH  /api/v1/projects/{project_id}             – update a draft or needs_info project
POST   /api/v1/projects/{project_id}/submit      – submit a draft project
POST   /api/v1/projects/{project_id}/resubmit    – resubmit a needs_info project
POST   /api/v1/projects/{project_id}/documents   – upload a supporting document
GET    /api/v1/projects/{project_id}/documents   – list project documents

All endpoints are protected: callers must present a valid bearer token with
role == 'supplier' (TRD sections 4, 8).

TRD sections 5.1, 5.2, 6, 7.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import List

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import SupplierUser
from app.db.models import (
    AuditEventEnum,
    DocumentTypeEnum,
    Project,
    ProjectAuditEvent,
    ProjectDocument,
    ProjectStatusEnum,
)
from app.db.session import get_db
from app.models.common import ErrorResponse
from app.models.project import (
    DocumentResponse,
    DocumentType,
    ProjectCreateRequest,
    ProjectResponse,
    ProjectUpdateRequest,
)

router = APIRouter(prefix="/projects", tags=["projects"])

PROTECTED_RESPONSES = {
    401: {"model": ErrorResponse, "description": "Missing, invalid or expired bearer token"},
    403: {"model": ErrorResponse, "description": "Supplier role required"},
}

# Maximum uploaded file size: 20 MB
MAX_FILE_BYTES = 20 * 1024 * 1024
ALLOWED_UPLOAD_MIME_TYPES = (
    "application/pdf",
    "image/jpeg",
    "image/png",
)
REQUIRED_DOCUMENT_TYPES = (
    DocumentType.registry_evidence,
    DocumentType.mrv_record,
    DocumentType.land_ownership_proof,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _project_to_response(project: Project) -> ProjectResponse:
    return ProjectResponse(
        id=str(project.id),
        supplier_id=str(project.supplier_id),
        title=project.title,
        description=project.description,
        methodology=project.methodology,
        geography=project.geography,
        baseline=project.baseline,
        expected_volume=project.expected_volume,
        status=project.status.value,
        review_reason=project.review_reason,
        submitted_at=project.submitted_at.isoformat() if project.submitted_at else None,
        created_at=project.created_at.isoformat(),
        updated_at=project.updated_at.isoformat(),
    )


def _project_snapshot(project: Project) -> str:
    """Return a JSON string capturing the current field values of a project."""
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


async def _append_audit_event(
    db: AsyncSession,
    project: Project,
    event: AuditEventEnum,
    actor_id: uuid.UUID | None = None,
) -> None:
    """Append an immutable audit event with a field snapshot."""
    evt = ProjectAuditEvent(
        project_id=project.id,
        actor_id=actor_id,
        event=event,
        snapshot_json=_project_snapshot(project),
        occurred_at=datetime.now(timezone.utc),
    )
    db.add(evt)


def _doc_to_response(doc: ProjectDocument) -> DocumentResponse:
    return DocumentResponse(
        id=str(doc.id),
        project_id=str(doc.project_id),
        doc_type=doc.doc_type.value,
        filename=doc.filename,
        storage_uri=doc.storage_uri,
        checksum=doc.checksum,
        uploaded_at=doc.uploaded_at.isoformat(),
    )


async def _get_owned_project(
    project_id: uuid.UUID,
    current_user: SupplierUser,
    db: AsyncSession,
) -> Project:
    """Fetch a project belonging to the authenticated supplier; raise 404 if absent."""
    result = await db.execute(
        select(Project).where(
            Project.id == project_id,
            Project.supplier_id == current_user.id,
        )
    )
    project = result.scalar_one_or_none()
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found.",
        )
    return project


# ---------------------------------------------------------------------------
# POST /api/v1/projects  – create draft project
# ---------------------------------------------------------------------------

@router.post(
    "",
    response_model=ProjectResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new draft project",
    responses={
        **PROTECTED_RESPONSES,
        422: {"model": ErrorResponse, "description": "Validation error"},
    },
)
async def create_project(
    body: ProjectCreateRequest,
    current_user: SupplierUser,
    db: AsyncSession = Depends(get_db),
) -> ProjectResponse:
    """
    Create a new carbon credit project in **draft** status.
    All required fields must be supplied; description is optional.

    TRD §5.1 – "Project submission form with draft + submitted states."
    """
    now = datetime.now(timezone.utc)
    project = Project(
        supplier_id=current_user.id,
        title=body.title,
        description=body.description,
        methodology=body.methodology,
        geography=body.geography,
        baseline=body.baseline,
        expected_volume=body.expected_volume,
        status=ProjectStatusEnum.draft,
        created_at=now,
        updated_at=now,
    )
    db.add(project)
    await db.flush()  # populate project.id before creating the audit event
    await _append_audit_event(db, project, AuditEventEnum.created, current_user.id)
    await db.commit()
    await db.refresh(project)
    return _project_to_response(project)


# ---------------------------------------------------------------------------
# GET /api/v1/projects  – list my projects
# ---------------------------------------------------------------------------

@router.get(
    "",
    response_model=List[ProjectResponse],
    summary="List the authenticated supplier's projects",
    responses=PROTECTED_RESPONSES,
)
async def list_projects(
    current_user: SupplierUser,
    db: AsyncSession = Depends(get_db),
) -> List[ProjectResponse]:
    """
    Return all projects belonging to the authenticated supplier,
    ordered by creation date descending.
    """
    result = await db.execute(
        select(Project)
        .where(Project.supplier_id == current_user.id)
        .order_by(Project.created_at.desc())
    )
    projects = result.scalars().all()
    return [_project_to_response(p) for p in projects]


# ---------------------------------------------------------------------------
# GET /api/v1/projects/{project_id}  – get a single project
# ---------------------------------------------------------------------------

@router.get(
    "/{project_id}",
    response_model=ProjectResponse,
    summary="Get a project by ID",
    responses={
        **PROTECTED_RESPONSES,
        404: {"model": ErrorResponse, "description": "Project not found"},
    },
)
async def get_project(
    project_id: uuid.UUID,
    current_user: SupplierUser,
    db: AsyncSession = Depends(get_db),
) -> ProjectResponse:
    project = await _get_owned_project(project_id, current_user, db)
    return _project_to_response(project)


# ---------------------------------------------------------------------------
# PATCH /api/v1/projects/{project_id}  – update a draft project
# ---------------------------------------------------------------------------

@router.patch(
    "/{project_id}",
    response_model=ProjectResponse,
    summary="Update a draft project (partial update)",
    responses={
        **PROTECTED_RESPONSES,
        404: {"model": ErrorResponse, "description": "Project not found"},
        409: {"model": ErrorResponse, "description": "Project is not in draft state"},
        422: {"model": ErrorResponse, "description": "Validation error"},
    },
)
async def update_project(
    project_id: uuid.UUID,
    body: ProjectUpdateRequest,
    current_user: SupplierUser,
    db: AsyncSession = Depends(get_db),
) -> ProjectResponse:
    """
    Partially update a project.  Only **draft** projects may be edited.

    TRD §5.1 – "Farmers can save a draft and return to complete later."
    """
    project = await _get_owned_project(project_id, current_user, db)
    if project.status not in (ProjectStatusEnum.draft, ProjectStatusEnum.needs_info):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only draft or needs_info projects can be updated.",
        )
    if body.title is not None:
        project.title = body.title
    if body.description is not None:
        project.description = body.description
    if body.methodology is not None:
        project.methodology = body.methodology
    if body.geography is not None:
        project.geography = body.geography
    if body.baseline is not None:
        project.baseline = body.baseline
    if body.expected_volume is not None:
        project.expected_volume = body.expected_volume
    project.updated_at = datetime.now(timezone.utc)
    await _append_audit_event(db, project, AuditEventEnum.updated, current_user.id)
    await db.commit()
    await db.refresh(project)
    return _project_to_response(project)


# ---------------------------------------------------------------------------
# POST /api/v1/projects/{project_id}/submit  – submit a draft project
# ---------------------------------------------------------------------------

@router.post(
    "/{project_id}/submit",
    response_model=ProjectResponse,
    summary="Submit a draft project for operator review",
    responses={
        **PROTECTED_RESPONSES,
        404: {"model": ErrorResponse, "description": "Project not found"},
        409: {"model": ErrorResponse, "description": "Project is already submitted"},
        422: {"model": ErrorResponse, "description": "Validation error"},
    },
)
async def submit_project(
    project_id: uuid.UUID,
    current_user: SupplierUser,
    db: AsyncSession = Depends(get_db),
) -> ProjectResponse:
    """
    Transition a project from **draft** → **submitted**.

    Once submitted, the project enters the operator review queue.
    Only draft projects can be submitted.

    TRD §5.1 – "Validation rules for required fields before submission."
    TRD §5.2 – Review queue receives submitted projects.
    """
    project = await _get_owned_project(project_id, current_user, db)
    if project.status != ProjectStatusEnum.draft:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only draft projects can be submitted.",
        )
    # Server-side validation: all required fields must be present before submission.
    missing_fields = []
    if project.methodology is None:
        missing_fields.append("methodology")
    if project.geography is None:
        missing_fields.append("geography")
    if project.baseline is None:
        missing_fields.append("baseline")
    if project.expected_volume is None:
        missing_fields.append("expected_volume")
    result = await db.execute(
        select(ProjectDocument.doc_type)
        .where(ProjectDocument.project_id == project.id)
        .distinct()
    )
    present_doc_types = {doc_type.value for doc_type in result.scalars()}
    missing_document_types = [
        doc_type.value
        for doc_type in REQUIRED_DOCUMENT_TYPES
        if doc_type.value not in present_doc_types
    ]
    validation_errors = []
    if missing_fields:
        validation_errors.append(
            f"required fields are missing: {', '.join(missing_fields)}"
        )
    if missing_document_types:
        validation_errors.append(
            "required document types are missing: "
            + ", ".join(missing_document_types)
        )
    if validation_errors:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Cannot submit: {'; '.join(validation_errors)}.",
        )
    now = datetime.now(timezone.utc)
    project.status = ProjectStatusEnum.submitted
    project.submitted_at = now
    project.updated_at = now
    await _append_audit_event(db, project, AuditEventEnum.submitted, current_user.id)
    await db.commit()
    await db.refresh(project)
    return _project_to_response(project)


# ---------------------------------------------------------------------------
# POST /api/v1/projects/{project_id}/documents  – upload a document
# ---------------------------------------------------------------------------

@router.post(
    "/{project_id}/documents",
    response_model=DocumentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a supporting document to a project",
    responses={
        **PROTECTED_RESPONSES,
        404: {"model": ErrorResponse, "description": "Project not found"},
        409: {"model": ErrorResponse, "description": "Submitted projects cannot receive new documents"},
        413: {"model": ErrorResponse, "description": "File too large (max 20 MB)"},
        415: {"model": ErrorResponse, "description": "Unsupported file type"},
        422: {"model": ErrorResponse, "description": "Validation error"},
    },
)
async def upload_document(
    project_id: uuid.UUID,
    current_user: SupplierUser,
    doc_type: DocumentType = Form(..., description="Type of document being uploaded"),
    file: UploadFile = File(..., description="Document file (max 20 MB)"),
    db: AsyncSession = Depends(get_db),
) -> DocumentResponse:
    """
    Attach a supporting document to a **draft** project.

    The file is read, its SHA-256 checksum computed, and metadata persisted.
    The `storage_uri` returned is a local-path reference (MVP); a production
    system would write to an object store and return a signed URL (TRD §3.1).

    Accepted document categories: `registry_evidence`, `mrv_record`,
    `land_ownership_proof`, `other`.
    Supported file formats: PDF, JPEG, PNG.

    TRD §5.1 – "Document upload support for registry evidence, MRV records,
                land ownership proofs."
    """
    project = await _get_owned_project(project_id, current_user, db)
    if project.status not in (ProjectStatusEnum.draft, ProjectStatusEnum.needs_info):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Documents can only be added to draft or needs_info projects.",
        )

    content_type = (file.content_type or "").split(";", 1)[0].strip().lower()
    if content_type not in ALLOWED_UPLOAD_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=(
                "Unsupported file type. Allowed MIME types: "
                + ", ".join(ALLOWED_UPLOAD_MIME_TYPES)
                + "."
            ),
        )

    content = await file.read(MAX_FILE_BYTES + 1)
    if len(content) > MAX_FILE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds the maximum allowed size of {MAX_FILE_BYTES // (1024 * 1024)} MB.",
        )

    checksum = hashlib.sha256(content).hexdigest()
    # Sanitize filename to prevent path traversal in storage_uri
    filename = Path(file.filename or "upload").name or "upload"
    # MVP: store path reference; replace with S3/GCS URI in production.
    storage_uri = f"local://uploads/{project_id}/{doc_type.value}/{filename}"

    doc = ProjectDocument(
        project_id=project.id,
        doc_type=DocumentTypeEnum[doc_type.value],
        filename=filename,
        storage_uri=storage_uri,
        checksum=checksum,
        uploaded_at=datetime.now(timezone.utc),
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)
    return _doc_to_response(doc)


# ---------------------------------------------------------------------------
# GET /api/v1/projects/{project_id}/documents  – list project documents
# ---------------------------------------------------------------------------

@router.get(
    "/{project_id}/documents",
    response_model=List[DocumentResponse],
    summary="List documents attached to a project",
    responses={
        **PROTECTED_RESPONSES,
        404: {"model": ErrorResponse, "description": "Project not found"},
    },
)
async def list_documents(
    project_id: uuid.UUID,
    current_user: SupplierUser,
    db: AsyncSession = Depends(get_db),
) -> List[DocumentResponse]:
    """Return all documents attached to a project owned by the authenticated supplier."""
    project = await _get_owned_project(project_id, current_user, db)
    result = await db.execute(
        select(ProjectDocument)
        .where(ProjectDocument.project_id == project.id)
        .order_by(ProjectDocument.uploaded_at.asc())
    )
    docs = result.scalars().all()
    return [_doc_to_response(d) for d in docs]


# ---------------------------------------------------------------------------
# POST /api/v1/projects/{project_id}/resubmit  – resubmit a needs_info project
# ---------------------------------------------------------------------------

@router.post(
    "/{project_id}/resubmit",
    response_model=ProjectResponse,
    summary="Resubmit a needs_info project for operator review",
    responses={
        **PROTECTED_RESPONSES,
        404: {"model": ErrorResponse, "description": "Project not found"},
        409: {"model": ErrorResponse, "description": "Project is not in needs_info state"},
        422: {"model": ErrorResponse, "description": "Validation error"},
    },
)
async def resubmit_project(
    project_id: uuid.UUID,
    current_user: SupplierUser,
    db: AsyncSession = Depends(get_db),
) -> ProjectResponse:
    """
    Transition a project from **needs_info** → **submitted** (re-enters the
    operator review queue).

    Only projects currently in `needs_info` state may be resubmitted.
    Projects in `approved`, `rejected`, or `in_review` state cannot be
    resubmitted.  A snapshot of the project fields is appended to the audit
    log with event = `resubmitted` so the full history is preserved.

    TRD §5.2 – "Resubmission transitions the project back to submitted /
                in_review state."
    TRD §5.2 – "Resubmission should create a new audit event with
                actor = farmer, event = resubmitted."
    """
    project = await _get_owned_project(project_id, current_user, db)
    if project.status != ProjectStatusEnum.needs_info:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Only projects in needs_info state can be resubmitted. "
                f"Current status: {project.status.value}."
            ),
        )
    # Validate that all required fields are still present.
    missing_fields = []
    if project.methodology is None:
        missing_fields.append("methodology")
    if project.geography is None:
        missing_fields.append("geography")
    if project.baseline is None:
        missing_fields.append("baseline")
    if project.expected_volume is None:
        missing_fields.append("expected_volume")
    result = await db.execute(
        select(ProjectDocument.doc_type)
        .where(ProjectDocument.project_id == project.id)
        .distinct()
    )
    present_doc_types = {doc_type.value for doc_type in result.scalars()}
    missing_document_types = [
        doc_type.value
        for doc_type in REQUIRED_DOCUMENT_TYPES
        if doc_type.value not in present_doc_types
    ]
    validation_errors = []
    if missing_fields:
        validation_errors.append(
            f"required fields are missing: {', '.join(missing_fields)}"
        )
    if missing_document_types:
        validation_errors.append(
            "required document types are missing: "
            + ", ".join(missing_document_types)
        )
    if validation_errors:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Cannot resubmit: {'; '.join(validation_errors)}.",
        )
    now = datetime.now(timezone.utc)
    project.status = ProjectStatusEnum.submitted
    project.review_reason = None  # clear prior feedback on resubmission
    project.updated_at = now
    await _append_audit_event(db, project, AuditEventEnum.resubmitted, current_user.id)
    await db.commit()
    await db.refresh(project)
    return _project_to_response(project)
