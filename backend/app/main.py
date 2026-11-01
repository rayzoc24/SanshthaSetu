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
        description="AICTE Approval Workflow Automation — Backend Service.",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # ── CORS ────────────────────────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Routers ─────────────────────────────────────────────────────────────
    from app.routers import admin, aph, auth, health  # noqa: PLC0415

    app.include_router(auth.router)
    app.include_router(health.router)
    app.include_router(admin.router)
    app.include_router(aph.router)

    return app


# Module-level app instance consumed by uvicorn.
app = create_app()
