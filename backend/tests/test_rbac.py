"""
Tests for RBAC enforcement on protected endpoints.

Target endpoint: GET /admin/ping  (requires main_admin role)

Proves:
  - Correct role (main_admin) → 200
  - Wrong role (college_admin) → 403
  - No token → 401
  - Expired token → 401
  - Token for is_active=False user → 401

All tests use a real PostgreSQL database. No mocking of dependencies.
"""

from __future__ import annotations

import time

import jwt
import pytest
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_PASSWORD = "Test@1234"
_PING_URL = "/admin/ping"


def _login_token(client: TestClient, email: str) -> str:
    r = client.post("/auth/login", json={"email": email, "password": _PASSWORD})
    assert r.status_code == 200, f"Setup login failed for {email}: {r.json()}"
    return r.json()["access_token"]


def _auth_header(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# GET /admin/ping — role enforcement
# ---------------------------------------------------------------------------

class TestAdminPingRBAC:

    def test_main_admin_gets_200(self, client, seed_users):
        """A main_admin token must be accepted by the main_admin-only endpoint."""
        token = _login_token(client, seed_users["main_admin"].email)
        r = client.get(_PING_URL, headers=_auth_header(token))
        assert r.status_code == 200
        assert r.json() == {"message": "pong"}

    def test_college_admin_gets_403(self, client, seed_users):
        """
        A college_admin token must be rejected with 403 on a main_admin endpoint.
        This is the core RBAC requirement: wrong role → forbidden, not 401.
        """
        token = _login_token(client, seed_users["college_admin"].email)
        r = client.get(_PING_URL, headers=_auth_header(token))
        assert r.status_code == 403
        assert "permissions" in r.json()["detail"].lower()

    def test_regional_officer_gets_403(self, client, seed_users):
        token = _login_token(client, seed_users["regional_officer"].email)
        r = client.get(_PING_URL, headers=_auth_header(token))
        assert r.status_code == 403

    def test_bureau_officer_gets_403(self, client, seed_users):
        token = _login_token(client, seed_users["bureau_officer"].email)
        r = client.get(_PING_URL, headers=_auth_header(token))
        assert r.status_code == 403

    def test_evc_member_gets_403(self, client, seed_users):
        token = _login_token(client, seed_users["evc_member"].email)
        r = client.get(_PING_URL, headers=_auth_header(token))
        assert r.status_code == 403

    def test_competent_authority_gets_403(self, client, seed_users):
        token = _login_token(client, seed_users["competent_authority"].email)
        r = client.get(_PING_URL, headers=_auth_header(token))
        assert r.status_code == 403


# ---------------------------------------------------------------------------
# Unauthenticated / invalid token cases
# ---------------------------------------------------------------------------

class TestAdminPingAuth:

    def test_no_token_returns_401(self, client):
        """Missing Authorization header → 401."""
        r = client.get(_PING_URL)
        assert r.status_code == 401

    def test_malformed_token_returns_401(self, client):
        """A token that is not valid JWT → 401."""
        r = client.get(_PING_URL, headers=_auth_header("this.is.garbage"))
        assert r.status_code == 401

    def test_expired_token_returns_401(self, client, seed_users):
        """A structurally valid but expired token → 401."""
        from app.config import settings  # noqa: PLC0415

        user = seed_users["main_admin"]
        payload = {
            "sub": str(user.id),
            "email": user.email,
            "role": "main_admin",
            "iat": int(time.time()) - 7200,
            "exp": int(time.time()) - 3600,  # expired 1 hour ago
        }
        expired_token = jwt.encode(payload, settings.jwt_secret, algorithm="HS256")
        r = client.get(_PING_URL, headers=_auth_header(expired_token))
        assert r.status_code == 401

    def test_inactive_user_returns_401(self, client, seed_users):
        """
        A valid, non-expired token for a user that has is_active=False → 401.
        The dependency reloads the user from DB on every request.
        """
        from app.config import settings  # noqa: PLC0415

        inactive = seed_users["inactive"]
        # Mint a fresh, non-expired token manually (can't login — account blocked).
        payload = {
            "sub": str(inactive.id),
            "email": inactive.email,
            "role": "main_admin",   # role that would normally be allowed
            "iat": int(time.time()),
            "exp": int(time.time()) + 3600,
        }
        token = jwt.encode(payload, settings.jwt_secret, algorithm="HS256")
        r = client.get(_PING_URL, headers=_auth_header(token))
        assert r.status_code == 401

    def test_token_with_nonexistent_user_id_returns_401(self, client):
        """Sub that is a valid UUID but no matching user row → 401."""
        from app.config import settings  # noqa: PLC0415
        import uuid  # noqa: PLC0415

        payload = {
            "sub": str(uuid.uuid4()),  # random UUID, no matching user
            "email": "ghost@example.com",
            "role": "main_admin",
            "iat": int(time.time()),
            "exp": int(time.time()) + 3600,
        }
        token = jwt.encode(payload, settings.jwt_secret, algorithm="HS256")
        r = client.get(_PING_URL, headers=_auth_header(token))
        assert r.status_code == 401

    def test_token_with_invalid_uuid_sub_returns_401(self, client):
        """Sub that is not a UUID at all → 401."""
        from app.config import settings  # noqa: PLC0415

        payload = {
            "sub": "not-a-uuid",
            "email": "x@x.com",
            "role": "main_admin",
            "iat": int(time.time()),
            "exp": int(time.time()) + 3600,
        }
        token = jwt.encode(payload, settings.jwt_secret, algorithm="HS256")
        r = client.get(_PING_URL, headers=_auth_header(token))
        assert r.status_code == 401
