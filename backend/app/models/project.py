"""
Pydantic request / response schemas for project intake endpoints.
TRD sections 5.1, 5.2, 6.
"""

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class ProjectStatus(str, Enum):
    draft = "draft"
    submitted = "submitted"
    in_review = "in_review"
    needs_info = "needs_info"
    approved = "approved"
    rejected = "rejected"


class DocumentType(str, Enum):
    registry_evidence = "registry_evidence"
    mrv_record = "mrv_record"
    land_ownership_proof = "land_ownership_proof"
    other = "other"


# ---------------------------------------------------------------------------
# Project schemas
# ---------------------------------------------------------------------------

class ProjectCreateRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=2000)
    methodology: str = Field(..., min_length=1, max_length=255)
    geography: str = Field(..., min_length=1, max_length=255)
    baseline: Optional[str] = Field(None, max_length=2000)
    expected_volume: Optional[float] = Field(None, gt=0, description="Expected annual CO2e tonnes")

    model_config = {
        "extra": "forbid",
        "json_schema_extra": {
            "example": {
                "title": "Rice Field Carbon Sequestration",
                "description": "Improved paddy management reducing CH4 emissions.",
                "methodology": "VM0015",
                "geography": "Punjab, India",
                "baseline": "Business-as-usual CH4 emissions from flooded paddy.",
                "expected_volume": 1500.0,
            }
        }
    }


class ProjectUpdateRequest(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=2000)
    methodology: Optional[str] = Field(None, min_length=1, max_length=255)
    geography: Optional[str] = Field(None, min_length=1, max_length=255)
    baseline: Optional[str] = Field(None, max_length=2000)
    expected_volume: Optional[float] = Field(None, gt=0, description="Expected annual CO2e tonnes")

    model_config = {
        "extra": "forbid",
        "json_schema_extra": {
            "example": {
                "geography": "Haryana, India",
            }
        }
    }


class ProjectResponse(BaseModel):
    id: str
    supplier_id: str
    title: str
    description: Optional[str]
    methodology: str
    geography: str
    baseline: Optional[str]
    expected_volume: Optional[float]
    status: str
    review_reason: Optional[str]
    submitted_at: Optional[str]
    created_at: str
    updated_at: str

    model_config = {"from_attributes": True}


class ProjectSubmissionReceipt(BaseModel):
    project_id: str
    current_status: str
    submitted_at: str
    message: str


class ProjectSubmissionResponse(ProjectResponse):
    submission_receipt: ProjectSubmissionReceipt


class ProjectTimelineEntry(BaseModel):
    status: str
    actor_role: str
    actor_id: str
    timestamp: str
    reason: Optional[str] = None


class ProjectTimelineResponse(BaseModel):
    project_id: str
    current_status: str
    submission_receipt: Optional[ProjectSubmissionReceipt] = None
    timeline: list[ProjectTimelineEntry]


# ---------------------------------------------------------------------------
# Audit log schemas (operator-facing)
# ---------------------------------------------------------------------------

class AuditEventResponse(BaseModel):
    """Full representation of a single audit event for operator queries."""
    id: str
    project_id: str
    event_type: str
    actor_id: Optional[str]
    actor_role: Optional[str]
    resource_type: Optional[str]
    resource_id: Optional[str]
    reason: Optional[str]
    timestamp: str


class AuditLogResponse(BaseModel):
    total: int
    events: list[AuditEventResponse]


# ---------------------------------------------------------------------------
# Document schemas
# ---------------------------------------------------------------------------

class DocumentResponse(BaseModel):
    id: str
    project_id: str
    doc_type: str
    filename: str
    storage_uri: str
    checksum: str
    uploaded_at: str

    model_config = {"from_attributes": True}
