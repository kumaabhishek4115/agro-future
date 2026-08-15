"""
Agro Future – Farmer Portal API

FastAPI application entry point.
Versioned REST API: /api/v1/...
TRD sections 7, 8.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.models.common import HealthResponse
from app.routers import auth, supplier

TAGS_METADATA = [
    {
        "name": "health",
        "description": "Liveness / readiness probes.",
    },
    {
        "name": "auth",
        "description": (
            "Supplier registration, email verification and JWT login. "
            "Public endpoints (TRD sections 4, 5.1)."
        ),
    },
    {
        "name": "supplier",
        "description": (
            "Farm profile management. Protected: requires a bearer token "
            "issued by `POST /api/v1/auth/login` with role `supplier` "
            "(TRD sections 5.1, 6, 8)."
        ),
    },
]

API_DESCRIPTION = """
REST API for the **Agro Future** farmer carbon credit marketplace.

Implements **Epic 1: Farmer Account Onboarding** (TRD sections 4, 5.1, 6, 7, 8).

### Authenticating in this UI
1. `POST /api/v1/auth/register` – creates a `pending_verification` account and
   returns `email_verification_token` (dev convenience only).
2. `POST /api/v1/auth/verify-email` – activates the account with that token.
3. `POST /api/v1/auth/login` – returns `access_token`.
4. Click **Authorize** at the top right and paste the `access_token`.

Protected endpoints are deny-by-default: a missing or invalid token returns
`401`, and a valid token with the wrong role returns `403`.
"""

app = FastAPI(
    title="Agro Future – Farmer Portal API",
    description=API_DESCRIPTION,
    version="1.0.0",
    openapi_tags=TAGS_METADATA,
    contact={"name": "Agro Future Engineering", "email": "engineering@agrofuture.example"},
    license_info={"name": "Proprietary"},
    servers=[{"url": "http://localhost:8000", "description": "Local development"}],
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    swagger_ui_parameters={
        "persistAuthorization": True,
        "displayRequestDuration": True,
        "docExpansion": "list",
        "filter": True,
        "tryItOutEnabled": True,
    },
)


# ---------------------------------------------------------------------------
# CORS – adjust allowed origins for production
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Next.js dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------
API_PREFIX = "/api/v1"

app.include_router(auth.router, prefix=API_PREFIX)
app.include_router(supplier.router, prefix=API_PREFIX)


@app.get(
    "/",
    tags=["health"],
    response_model=HealthResponse,
    summary="Liveness probe",
)
async def health_check() -> HealthResponse:
    """Simple liveness probe."""
    return HealthResponse(status="ok", service="agro-future-api")

