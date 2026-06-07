"""
FinSight — FastAPI Application Entry Point.

Registers all routers, middleware, and exception handlers.
"""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.core.exceptions import register_exception_handlers

# Configure logging
logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

# Create app
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=(
        "FinSight API — Connect to Tally Prime, run audit rules, "
        "map to MCA Schedule III, and generate CA-ready reports."
    ),
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── Middleware ────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Exception Handlers ───────────────────────────────────────────────────
register_exception_handlers(app)

# ── Routers ──────────────────────────────────────────────────────────────
from app.api.auth import router as auth_router  # noqa: E402
from app.api.clients import router as clients_router  # noqa: E402
from app.api.tally_sync import router as tally_sync_router  # noqa: E402
from app.api.audit import router as audit_router  # noqa: E402
from app.api.schedule_iii import router as schedule_iii_router  # noqa: E402
from app.api.reports import router as reports_router  # noqa: E402

app.include_router(auth_router)
app.include_router(clients_router)
app.include_router(tally_sync_router)
app.include_router(audit_router)
app.include_router(schedule_iii_router)
app.include_router(reports_router)


# ── Health Check ─────────────────────────────────────────────────────────
@app.get("/api/health", tags=["System"])
async def health_check():
    return {
        "status": "healthy",
        "app": settings.app_name,
        "version": settings.app_version,
    }


@app.get("/", tags=["System"])
async def root():
    return {
        "app": settings.app_name,
        "version": settings.app_version,
        "docs": "/docs",
    }
