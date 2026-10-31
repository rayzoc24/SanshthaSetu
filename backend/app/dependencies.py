"""
Shared FastAPI dependencies.

require_roles(allowed_roles)
    Returns a sync dependency function that:
      1. Extracts the Bearer token from the Authorization header via HTTPBearer.
      2. Decodes and validates the JWT (raises 401 on failure).
      3. Validates the sub claim is a well-formed UUID (raises 401 on failure).
      4. Reloads the User row from the database on every request — never trusts
         stale data cached in the token payload.
      5. Rejects disabled accounts (is_active=False) with 401.
      6. Rejects callers whose role is not in allowed_roles with 403.
      7. Returns the User ORM object to the endpoint.

Swagger UI: uses HTTPBearer so the Authorize dialog accepts a pasted raw token.
"""

from __future__ import annotations

import uuid

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import User
from app.services.auth_service import decode_token

# auto_error=False: we handle the missing-credentials case ourselves
# so we can return 401 (not 403) when no Authorization header is provided.
_bearer = HTTPBearer(auto_error=False)


def require_roles(allowed_roles: list[str]):
    """
    Factory that returns a reusable sync dependency enforcing role-based access.

    Usage on an endpoint:
        @router.get("/some-path")
        def handler(user: User = Depends(require_roles(["main_admin"]))):
            ...

    Or called directly (e.g. inside /auth/me):
        user = require_roles(all_roles)(credentials=creds, db=db)
    """

    def dependency(
        credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
        db: Session = Depends(get_db),
    ) -> User:
        # No Authorization header → 401 (not 403).
        if credentials is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authenticated",
            )

        token = credentials.credentials

        # 1. Decode and validate the JWT — raises 401 on any failure.
        payload = decode_token(token, settings.jwt_secret)

        # 2. Extract user UUID (decode_token already validated it is a UUID).
        try:
            user_id = uuid.UUID(payload["sub"])
        except (ValueError, KeyError):
            # Should never reach here after decode_token's validation,
            # but guard defensively.
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: sub is not a valid UUID",
            )

        # 3. Reload the user from the database on every request.
        #    This catches deactivated accounts without waiting for token expiry.
        user: User | None = db.get(User, user_id)
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
            )

        # 4. Reject disabled accounts.
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Account is disabled",
            )

        # 5. Load role name — relationship is lazy-loaded here.
        role_name: str = user.role.name

        # 6. Enforce role membership.
        if role_name not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )

        return user

    return dependency
