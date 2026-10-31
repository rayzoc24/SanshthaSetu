"""
/auth endpoints

POST /auth/login  — validate credentials, return JWT
GET  /auth/me     — return current user profile (any authenticated role)
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import User
from app.schemas.auth import LoginRequest, MeResponse, TokenResponse
from app.services.audit_service import record_audit
from app.services.auth_service import create_access_token, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])

# All six role names — any authenticated, active user may call /me.
_ALL_ROLES: list[str] = [
    "college_admin",
    "main_admin",
    "regional_officer",
    "bureau_officer",
    "evc_member",
    "competent_authority",
]


def _client_ip(request: Request) -> str | None:
    """
    Return the real client IP address.
    Prefers X-Forwarded-For (set by Render's reverse proxy).
    Falls back to request.client.host.
    """
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else None


# ---------------------------------------------------------------------------
# POST /auth/login
# ---------------------------------------------------------------------------

@router.post(
    "/login",
    response_model=TokenResponse,
    responses={401: {"description": "Invalid credentials"}},
    summary="Obtain a JWT by supplying email and password",
)
def login(
    body: LoginRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> TokenResponse:
    """
    Authenticate a user and return a signed JWT.

    Audit rows are written for every attempt — success and failure — via an
    independent DB session so they persist even when the endpoint returns 401.
    """
    ip = _client_ip(request)

    # 1. Resolve user by email.
    user: User | None = db.query(User).filter(User.email == body.email).first()

    if user is None:
        record_audit(
            action="login_failed",
            detail=f"unknown email: {body.email}",
            ip_address=ip,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    # 2. Verify password.
    if not verify_password(body.password, user.password_hash):
        record_audit(
            action="login_failed",
            user_id=user.id,
            detail=f"wrong password for: {body.email}",
            ip_address=ip,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    # 3. Reject inactive accounts.
    if not user.is_active:
        record_audit(
            action="login_blocked",
            user_id=user.id,
            detail=f"inactive account: {body.email}",
            ip_address=ip,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account is disabled",
        )

    # 4. Issue JWT and record success.
    token = create_access_token(user, settings.jwt_expire_hours)

    record_audit(
        action="login",
        user_id=user.id,
        entity_type="user",
        entity_id=user.id,
        ip_address=ip,
    )

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        role=user.role.name,
    )


# ---------------------------------------------------------------------------
# GET /auth/me
# ---------------------------------------------------------------------------
# NOTE: require_roles is imported here — NOT at module top — because this
# router module is itself imported inside create_app() in main.py, which runs
# after all packages are initialised.  Keeping the import local to the
# endpoint avoids any edge-case where a tool (e.g. alembic env.py) imports
# app.database / app.models directly without going through main.py.
# At request time the import is always already cached by Python's module
# system, so there is zero runtime overhead.

@router.get(
    "/me",
    response_model=MeResponse,
    responses={401: {"description": "Not authenticated"}},
    summary="Return the profile of the currently authenticated user",
)
def me(request: Request, db: Session = Depends(get_db)) -> MeResponse:
    """
    Decode the bearer token, reload the user from DB, and return their profile.
    Token validation and active-user check are performed inside require_roles.
    """
    from app.dependencies import require_roles  # noqa: PLC0415
    from fastapi.security import HTTPAuthorizationCredentials  # noqa: PLC0415

    # Extract the bearer token from the Authorization header manually,
    # since we are calling the dependency as a plain function rather than
    # via FastAPI's DI system.
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.lower().startswith("bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )
    token = auth_header[7:].strip()
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

    current_user: User = require_roles(_ALL_ROLES)(credentials=credentials, db=db)

    return MeResponse(
        id=current_user.id,
        email=current_user.email,
        full_name=current_user.full_name,
        role=current_user.role.name,
        institution_id=current_user.institution_id,
        region=current_user.region,
    )
