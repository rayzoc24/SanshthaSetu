"""
Pure authentication helpers — no FastAPI dependencies, fully unit-testable.

Functions
─────────
hash_password(plain)          → argon2 hash string
verify_password(plain, hashed) → bool
create_access_token(user, expire_hours) → signed JWT string
decode_token(token, secret)    → dict payload  (raises HTTPException 401 on failure)
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerificationError, VerifyMismatchError, InvalidHashError
from fastapi import HTTPException, status

if TYPE_CHECKING:
    from app.models import User


# ---------------------------------------------------------------------------
# Argon2 hasher — module-level singleton, thread-safe.
# Default parameters (time_cost=3, memory_cost=65536, parallelism=4)
# are OWASP-recommended for argon2id.
# ---------------------------------------------------------------------------
_ph = PasswordHasher()


def hash_password(plain: str) -> str:
    """Return an argon2id hash of plain."""
    return _ph.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    """
    Return True if plain matches hashed, False otherwise.
    Never raises — all argon2 exceptions are caught and mapped to False.
    """
    try:
        return _ph.verify(hashed, plain)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


# ---------------------------------------------------------------------------
# JWT
# ---------------------------------------------------------------------------

def create_access_token(user: "User", expire_hours: int) -> str:
    """
    Build and sign a HS256 JWT.

    Payload:
        sub   — user UUID as str
        email — user email
        role  — role name string
        exp   — UTC expiry timestamp
        iat   — UTC issued-at timestamp
    """
    from app.config import settings  # local import avoids circular at module load

    now = datetime.now(tz=timezone.utc)
    payload = {
        "sub": str(user.id),
        "email": user.email,
        "role": user.role.name,
        "iat": now,
        "exp": now + timedelta(hours=expire_hours),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


def decode_token(token: str, secret: str) -> dict:
    """
    Decode and verify a JWT.

    Returns the payload dict on success.
    Raises HTTPException(401) on:
      - expired token
      - invalid signature / malformed token
      - sub field is not a valid UUID string
    """
    try:
        payload: dict = jwt.decode(
            token,
            secret,
            algorithms=["HS256"],
            options={"require": ["sub", "exp", "role"]},
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
        )
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )

    # Validate that sub is a well-formed UUID — reject tokens with garbage subs.
    try:
        uuid.UUID(payload["sub"])
    except (ValueError, KeyError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token: sub is not a valid UUID",
        )

    return payload
