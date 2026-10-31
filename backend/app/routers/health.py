"""
Health check endpoints — no authentication required.

GET /health     Process-level liveness probe. No DB call.
                Used by Render's health check; always returns 200 while the
                process is alive, even if the database is unreachable.

GET /health/db  Database connectivity probe.
                Executes SELECT 1. Returns 200 on success, 503 on failure.
                Use this to verify Neon connectivity after deployment.
"""

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy import text

router = APIRouter(tags=["health"])


@router.get(
    "/health",
    summary="Process liveness — no DB call",
    response_description="Always 200 while the process is running",
)
def health() -> dict:
    """
    Lightweight liveness probe.
    Render's health-check URL should point here so that a DB outage does not
    cause the web service to be marked as down.
    """
    return {"status": "ok"}


@router.get(
    "/health/db",
    summary="Database connectivity probe",
    response_description="200 if the database is reachable, 503 otherwise",
)
def health_db() -> JSONResponse:
    """
    Verifies that the application can reach PostgreSQL by executing SELECT 1.
    Opens its own connection so that a failure at any level (engine, pool,
    network) is caught and returned as HTTP 503 rather than a 500.
    """
    try:
        from app.database import SessionLocal  # noqa: PLC0415

        with SessionLocal() as db:
            db.execute(text("SELECT 1"))
        return JSONResponse(
            status_code=200,
            content={"status": "ok", "database": "ok"},
        )
    except Exception as exc:  # noqa: BLE001
        return JSONResponse(
            status_code=503,
            content={"status": "error", "database": "unreachable", "detail": str(exc)},
        )
