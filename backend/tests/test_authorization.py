from __future__ import annotations

import uuid

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.core.authorization import ensure_supplier_owns_resource
from app.models.project import ProjectCreateRequest, ProjectUpdateRequest
from app.models.supplier import SupplierProfileRequest


def test_ensure_supplier_owns_resource_allows_matching_owner():
    owner_id = uuid.uuid4()
    ensure_supplier_owns_resource(
        resource_owner_id=owner_id,
        current_user_id=owner_id,
        resource_name="project",
    )


def test_ensure_supplier_owns_resource_rejects_cross_tenant_access():
    with pytest.raises(HTTPException) as exc_info:
        ensure_supplier_owns_resource(
            resource_owner_id=uuid.uuid4(),
            current_user_id=uuid.uuid4(),
            resource_name="project",
        )

    assert exc_info.value.status_code == 403
    assert "another supplier's project" in exc_info.value.detail


@pytest.mark.parametrize(
    ("model_class", "payload", "owner_field"),
    [
        (
            ProjectCreateRequest,
            {
                "title": "Rice Field Carbon Sequestration",
                "methodology": "VM0015",
                "geography": "Punjab, India",
                "supplier_id": str(uuid.uuid4()),
            },
            "supplier_id",
        ),
        (
            ProjectUpdateRequest,
            {"geography": "Haryana, India", "supplier_id": str(uuid.uuid4())},
            "supplier_id",
        ),
        (
            SupplierProfileRequest,
            {"geography": "Kenya", "user_id": str(uuid.uuid4())},
            "user_id",
        ),
    ],
)
def test_farmer_request_models_forbid_client_supplied_owner_fields(
    model_class,
    payload,
    owner_field,
):
    with pytest.raises(ValidationError) as exc_info:
        model_class(**payload)

    assert owner_field in str(exc_info.value)
