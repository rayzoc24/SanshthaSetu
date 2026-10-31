from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings


def create_app() -> FastAPI:
    """
    Application factory.
    Validates config, registers middleware, mounts routers.
    """
    # Fail fast at startup if required settings are misconfigured.
    settings.validate_required()

    app = FastAPI(
        title="SanshthaSetu API",
        version="0.1.0",
        description="AICTE Approval Workflow Automation — Module 0 foundation.",
        # Swagger UI is available in all environments for developer convenience.
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # ── CORS ────────────────────────────────────────────────────────────────
    # allow_credentials=False per design amendment 8.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Routers ─────────────────────────────────────────────────────────────
    # Imported here (not at module level) to avoid circular imports when
    # routers import from app.dependencies which imports from app.database.
    from app.routers import auth, health, admin  # noqa: PLC0415

    app.include_router(auth.router)
    app.include_router(health.router)
    app.include_router(admin.router)

    return app


# Module-level app instance consumed by uvicorn.
app = create_app()
