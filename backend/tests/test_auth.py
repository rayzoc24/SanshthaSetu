"""
Tests for POST /auth/login and GET /auth/me.

All tests use a real PostgreSQL database (TEST_DATABASE_URL).
Audit-row assertions filter by the unique test email address in `detail`,
never by counting all rows in the table.
"""

from __future__ import annotations

import time

import jwt
import pytest
from fastapi.testclient import TestClient

from tests.conftest import query_audit


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_PASSWORD = "Test@1234"
_WRONG_PW = "WrongPassword99!"


def _login(client: TestClient, email: str, password: str):
    return client.post("/auth/login", json={"email": email, "password": password})


# ---------------------------------------------------------------------------
# POST /auth/login — happy path
# ---------------------------------------------------------------------------

class TestLoginSuccess:
    def test_returns_200(self, client, seed_users):
        user = seed_users["main_admin"]
        r = _login(client, user.email, _PASSWORD)
        assert r.status_code == 200

    def test_response_contains_access_token(self, client, seed_users):
        user = seed_users["main_admin"]
        r = _login(client, user.email, _PASSWORD)
        body = r.json()
        assert "access_token" in body
        assert body["token_type"] == "bearer"

    def test_role_returned_in_response(self, client, seed_users):
        user = seed_users["college_admin"]
        r = _login(client, user.email, _PASSWORD)
        assert r.json()["role"] == "college_admin"

    def test_jwt_payload_contains_expected_claims(self, client, seed_users):
        from app.config import settings  # noqa: PLC0415

        user = seed_users["main_admin"]
        r = _login(client, user.email, _PASSWORD)
        token = r.json()["access_token"]
        payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])

        assert payload["email"] == user.email
        assert payload["role"] == "main_admin"
        assert str(user.id) == payload["sub"]
        assert "exp" in payload
        assert "iat" in payload

    def test_successful_login_creates_audit_row(self, client, seed_users):
        user = seed_users["regional_officer"]
        _login(client, user.email, _PASSWORD)

        rows = query_audit(user.email, "login")
        assert len(rows) >= 1, "Expected at least one 'login' audit row"


# ---------------------------------------------------------------------------
# POST /auth/login — failure cases
# ---------------------------------------------------------------------------

class TestLoginFailures:
    def test_wrong_password_returns_401(self, client, seed_users):
        user = seed_users["main_admin"]
        r = _login(client, user.email, _WRONG_PW)
        assert r.status_code == 401

    def test_wrong_password_detail_message(self, client, seed_users):
        user = seed_users["main_admin"]
        r = _login(client, user.email, _WRONG_PW)
        assert "Invalid email or password" in r.json()["detail"]

    def test_wrong_password_creates_audit_row(self, client, seed_users):
        user = seed_users["bureau_officer"]
        _login(client, user.email, _WRONG_PW)

        rows = query_audit(user.email, "login_failed")
        assert len(rows) >= 1, "Expected 'login_failed' audit row for wrong password"

    def test_unknown_email_returns_401(self, client):
        r = _login(client, "nobody_xyz_12345@example.com", _PASSWORD)
        assert r.status_code == 401

    def test_unknown_email_creates_audit_row(self, client):
        unique_email = "unknown_audit_test_99@example.com"
        _login(client, unique_email, _PASSWORD)

        rows = query_audit(unique_email, "login_failed")
        assert len(rows) >= 1, "Expected 'login_failed' audit row for unknown email"

    def test_inactive_user_returns_401(self, client, seed_users):
        user = seed_users["inactive"]
        # Use the known hash — inactive user has Test@1234.
        r = _login(client, user.email, _PASSWORD)
        assert r.status_code == 401

    def test_inactive_user_detail_message(self, client, seed_users):
        user = seed_users["inactive"]
        r = _login(client, user.email, _PASSWORD)
        assert "disabled" in r.json()["detail"].lower()

    def test_missing_email_field_returns_422(self, client):
        r = client.post("/auth/login", json={"password": _PASSWORD})
        assert r.status_code == 422

    def test_missing_password_field_returns_422(self, client):
        r = client.post("/auth/login", json={"email": "a@b.com"})
        assert r.status_code == 422

    def test_invalid_email_format_returns_422(self, client):
        r = _login(client, "not-an-email", _PASSWORD)
        assert r.status_code == 422


# ---------------------------------------------------------------------------
# GET /auth/me
# ---------------------------------------------------------------------------

class TestMe:
    def _get_token(self, client, seed_users, role: str) -> str:
        user = seed_users[role]
        r = _login(client, user.email, _PASSWORD)
        assert r.status_code == 200, f"Login failed for role={role}"
        return r.json()["access_token"]

    def test_valid_token_returns_200(self, client, seed_users):
        token = self._get_token(client, seed_users, "main_admin")
        r = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200

    def test_me_returns_correct_email(self, client, seed_users):
        user = seed_users["main_admin"]
        token = self._get_token(client, seed_users, "main_admin")
        r = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert r.json()["email"] == user.email

    def test_me_returns_correct_role(self, client, seed_users):
        token = self._get_token(client, seed_users, "evc_member")
        r = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert r.json()["role"] == "evc_member"

    def test_me_returns_institution_id_for_college_admin(self, client, seed_users):
        token = self._get_token(client, seed_users, "college_admin")
        r = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
        body = r.json()
        assert body["institution_id"] is not None

    def test_no_token_returns_401(self, client):
        r = client.get("/auth/me")
        assert r.status_code == 401

    def test_malformed_token_returns_401(self, client):
        r = client.get("/auth/me", headers={"Authorization": "Bearer not.a.jwt"})
        assert r.status_code == 401

    def test_expired_token_returns_401(self, client, seed_users):
        from app.config import settings   # noqa: PLC0415
        from datetime import timedelta    # noqa: PLC0415

        user = seed_users["main_admin"]
        # Build a token with negative expiry (already expired).
        payload = {
            "sub": str(user.id),
            "email": user.email,
            "role": "main_admin",
            "iat": int(time.time()) - 7200,
            "exp": int(time.time()) - 3600,  # expired 1 hour ago
        }
        expired_token = jwt.encode(payload, settings.jwt_secret, algorithm="HS256")

        r = client.get("/auth/me", headers={"Authorization": f"Bearer {expired_token}"})
        assert r.status_code == 401
        assert "expired" in r.json()["detail"].lower()
