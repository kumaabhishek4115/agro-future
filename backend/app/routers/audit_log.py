"""
Operator-facing audit log endpoint.

GET /api/v1/audit-log  – query the append-only audit trail

Protected: callers must present a valid bearer token with role == 'operator'
or 'admin'.

TRD sections 5.2, 8, 10.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import OperatorUser
from app.db.models import Project, ProjectAuditEvent, User
from app.db.session import get_db
from app.models.common import ErrorResponse
from app.models.project import AuditEventResponse, AuditLogResponse

router = APIRouter(prefix="/audit-log", tags=["audit-log"])

PROTECTED_RESPONSES = {
    401: {"model": ErrorResponse, "description": "Missing, invalid or expired bearer token"},
    403: {"model": ErrorResponse, "description": "Operator or admin role required"},
}


def _audit_event_to_response(event: ProjectAuditEvent) -> AuditEventResponse:
    return AuditEventResponse(
        id=str(event.id),
        project_id=str(event.project_id),
        event_type=event.event.value,
        actor_id=str(event.actor_id) if event.actor_id is not None else None,
        actor_role=event.actor_role,
        resource_type=event.resource_type,
        resource_id=str(event.resource_id) if event.resource_id is not None else None,
        reason=event.reason,
        timestamp=event.occurred_at.isoformat(),
    )


# ---------------------------------------------------------------------------
# GET /api/v1/audit-log  – operator audit log query
# ---------------------------------------------------------------------------

@router.get(
    "",
    response_model=AuditLogResponse,
    summary="Query the audit log for a project or farmer (operator only)",
    responses={
        **PROTECTED_RESPONSES,
        400: {"model": ErrorResponse, "description": "project_id or supplier_id must be provided"},
        404: {"model": ErrorResponse, "description": "Project or supplier not found"},
    },
)
async def query_audit_log(
    current_user: OperatorUser,
    db: AsyncSession = Depends(get_db),
    project_id: uuid.UUID | None = Query(None, description="Filter by project ID"),
    supplier_id: uuid.UUID | None = Query(None, description="Filter by supplier/farmer user ID"),
) -> AuditLogResponse:
    """
    Return the full audit event log filtered by project or supplier.

    At least one of `project_id` or `supplier_id` must be supplied.
    Results are ordered chronologically (oldest first).

    Only operators and admins may access this endpoint.

    TRD §5.2 – Review workflow audit requirements
    TRD §8   – Security and audit
    TRD §10  – Compliance and data retention
    """
    if project_id is None and supplier_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one of project_id or supplier_id must be provided.",
        )

    query = select(ProjectAuditEvent).join(
        Project, ProjectAuditEvent.project_id == Project.id
    )

    if project_id is not None:
        project_exists = await db.execute(
            select(Project.id).where(Project.id == project_id)
        )
        if project_exists.scalar_one_or_none() is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found.",
            )
        query = query.where(ProjectAuditEvent.project_id == project_id)

    if supplier_id is not None:
        supplier_exists = await db.execute(
            select(User.id).where(User.id == supplier_id)
        )
        if supplier_exists.scalar_one_or_none() is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Supplier not found.",
            )
        query = query.where(Project.supplier_id == supplier_id)

    query = query.order_by(ProjectAuditEvent.occurred_at.asc())
    result = await db.execute(query)
    events = result.scalars().all()

    return AuditLogResponse(
        total=len(events),
        events=[_audit_event_to_response(e) for e in events],
    )
