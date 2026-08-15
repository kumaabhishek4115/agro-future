"""
Agro Future – Farmer Portal API

FastAPI application entry point.
Versioned REST API: /api/v1/...
TRD sections 7, 8.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import auth, supplier

app = FastAPI(
    title="Agro Future – Farmer Portal API",
    description=(
        "REST API for the Agro Future farmer carbon credit marketplace. "
        "Implements Epic 1: Farmer Account Onboarding (TRD sections 4, 5.1, 6, 7, 8)."
    ),
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
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


@app.get("/", tags=["health"])
async def health_check() -> dict[str, str]:
    """Simple liveness probe."""
    return {"status": "ok", "service": "agro-future-api"}
