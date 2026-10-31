"""
Pydantic schemas for the /auth endpoints.
"""

import uuid
from typing import Optional

from pydantic import BaseModel, EmailStr


class LoginRequest(BaseModel):
    """Body accepted by POST /auth/login."""

    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    """
    Returned on successful login.
    role is included so the frontend can redirect immediately
    without a second /auth/me call.
    """

    access_token: str
    token_type: str = "bearer"
    role: str


class MeResponse(BaseModel):
    """Returned by GET /auth/me."""

    id: uuid.UUID
    email: str
    full_name: str
    role: str
    institution_id: Optional[uuid.UUID] = None
    region: Optional[str] = None
