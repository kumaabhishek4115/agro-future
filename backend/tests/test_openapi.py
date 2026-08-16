"""
Tests for the OpenAPI schema and Swagger UI / ReDoc documentation endpoints.
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient

OPENAPI_URL = "/api/openapi.json"

EXPECTED_OPERATIONS = {
    ("/", "get"),
    ("/api/v1/auth/register", "post"),
    ("/api/v1/auth/login", "post"),
    ("/api/v1/auth/verify-email", "post"),
    ("/api/v1/auth/verify-mobile", "post"),
    ("/api/v1/auth/resend-mobile-code", "post"),
    ("/api/v1/auth/logout", "post"),
    ("/api/v1/supplier/profile", "get"),
    ("/api/v1/supplier/profile", "post"),
    ("/api/v1/projects", "post"),
    ("/api/v1/projects", "get"),
    ("/api/v1/projects/{project_id}", "get"),
    ("/api/v1/projects/{project_id}", "patch"),
    ("/api/v1/projects/{project_id}/resubmit", "post"),
    ("/api/v1/projects/{project_id}/submit", "post"),
    ("/api/v1/projects/{project_id}/documents", "post"),
    ("/api/v1/projects/{project_id}/documents", "get"),
}


@pytest.mark.asyncio
async def test_openapi_schema_is_served(client: AsyncClient) -> None:
    resp = await client.get(OPENAPI_URL)
    assert resp.status_code == 200
    schema = resp.json()
    assert schema["openapi"].startswith("3.")
    assert schema["info"]["title"] == "Agro Future – Farmer Portal API"
    assert schema["info"]["version"] == "1.0.0"


@pytest.mark.asyncio
async def test_all_endpoints_documented(client: AsyncClient) -> None:
    schema = (await client.get(OPENAPI_URL)).json()
    operations = {
        (path, method)
        for path, methods in schema["paths"].items()
        for method in methods
    }
    assert operations == EXPECTED_OPERATIONS


@pytest.mark.asyncio
async def test_every_operation_has_summary_and_tag(client: AsyncClient) -> None:
    schema = (await client.get(OPENAPI_URL)).json()
    for path, methods in schema["paths"].items():
        for method, operation in methods.items():
            assert operation.get("summary"), f"{method.upper()} {path} missing summary"
            assert operation.get("tags"), f"{method.upper()} {path} missing tags"


@pytest.mark.asyncio
async def test_protected_endpoints_declare_bearer_security(client: AsyncClient) -> None:
    schema = (await client.get(OPENAPI_URL)).json()
    assert "BearerAuth" in schema["components"]["securitySchemes"]

    for method in ("get", "post"):
        operation = schema["paths"]["/api/v1/supplier/profile"][method]
        schemes = {name for entry in operation["security"] for name in entry}
        assert "BearerAuth" in schemes
        assert {"401", "403"} <= set(operation["responses"])


@pytest.mark.asyncio
async def test_public_auth_endpoints_are_unsecured(client: AsyncClient) -> None:
    schema = (await client.get(OPENAPI_URL)).json()
    for path in ("/api/v1/auth/register", "/api/v1/auth/login", "/api/v1/auth/verify-email"):
        assert "security" not in schema["paths"][path]["post"]


@pytest.mark.asyncio
async def test_error_responses_documented(client: AsyncClient) -> None:
    schema = (await client.get(OPENAPI_URL)).json()
    assert "409" in schema["paths"]["/api/v1/auth/register"]["post"]["responses"]
    assert "401" in schema["paths"]["/api/v1/auth/login"]["post"]["responses"]
    assert "400" in schema["paths"]["/api/v1/auth/verify-email"]["post"]["responses"]
    assert "404" in schema["paths"]["/api/v1/supplier/profile"]["get"]["responses"]
    assert "ErrorResponse" in schema["components"]["schemas"]


@pytest.mark.asyncio
async def test_request_schemas_include_examples(client: AsyncClient) -> None:
    schemas = (await client.get(OPENAPI_URL)).json()["components"]["schemas"]
    for name in ("RegisterRequest", "LoginRequest", "SupplierProfileRequest"):
        assert "example" in schemas[name], f"{name} missing OpenAPI example"


@pytest.mark.asyncio
@pytest.mark.parametrize("url", ["/api/docs", "/api/redoc"])
async def test_documentation_ui_endpoints(client: AsyncClient, url: str) -> None:
    resp = await client.get(url)
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]
