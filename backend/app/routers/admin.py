"""
Admin portal endpoints.

GET /admin/ping  — protected by main_admin role; used by RBAC tests.
"""

from fastapi import APIRouter, Depends

from app.dependencies import require_roles
from app.models import User

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get(
    "/ping",
    summary="Admin liveness probe — requires main_admin role",
    response_description="Returns pong when the caller has the main_admin role",
)
def ping(
    _current_user: User = Depends(require_roles(["main_admin"])),
) -> dict:
    """
    Simple protected endpoint used to verify RBAC enforcement:
    - main_admin token   → 200 {"message": "pong"}
    - any other role     → 403
    - no token / expired → 401
    """
    return {"message": "pong"}
