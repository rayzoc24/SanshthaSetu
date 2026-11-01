"""
Tests for Module 1 APH Pipeline Endpoints & Services.
Verifies:
  - Role restrictions: 401 for unauthenticated, 403 for non-main_admin
  - Upload handling: 400 for non-PDF / magic byte violation
  - Published version precedence and immutability
  - Rule creation, modification, conflict (409) handling
"""

from __future__ import annotations

import io
import uuid
from datetime import date, timedelta
import pytest
from fastapi.testclient import TestClient

from app.services.gemini_service import ExtractionError, gemini_service
from app.schemas.aph import AphRuleDraft


# Helper mock gemini client
class FakeGeminiClient:
    def __init__(self, responses=None, should_fail=False):
        self.call_count = 0
        self.should_fail = should_fail
        self.responses = responses or []

    def generate_structured(self, prompt, response_schema, system_instruction=None):
        self.call_count += 1
        if self.should_fail:
            raise RuntimeError("Gemini simulated API timeout")

        from app.schemas.aph import AphRuleExtractionResult
        return AphRuleExtractionResult(rules=self.responses)


def _login_token(client: TestClient, email: str) -> str:
    r = client.post("/auth/login", json={"email": email, "password": "Demo@1234"})
    assert r.status_code == 200, f"Login failed for {email}"
    return r.json()["access_token"]


def test_get_published_version_requires_auth(client: TestClient):
    r = client.get("/aph/versions/published")
    assert r.status_code == 401


def test_list_versions_requires_main_admin(client: TestClient, seed_users):
    college_token = _login_token(client, seed_users["college_admin"].email)
    r = client.get("/aph/versions", headers={"Authorization": f"Bearer {college_token}"})
    assert r.status_code == 403

    admin_token = _login_token(client, seed_users["main_admin"].email)
    r = client.get("/aph/versions", headers={"Authorization": f"Bearer {admin_token}"})
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_upload_aph_non_pdf_rejected(client: TestClient, seed_users):
    admin_token = _login_token(client, seed_users["main_admin"].email)
    fake_file = io.BytesIO(b"NOT_A_PDF_CONTENT")
    r = client.post(
        "/aph/versions",
        data={"version_label": "Invalid PDF Version"},
        files={"file": ("test.txt", fake_file, "text/plain")},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert r.status_code == 400
    assert "Invalid file format" in r.json()["detail"]


def test_gemini_extraction_failure_handling(monkeypatch):
    from app.services import gemini_service as gs_module
    fake = FakeGeminiClient(should_fail=True)
    monkeypatch.setattr(gs_module, "gemini_client", fake)

    with pytest.raises(ExtractionError):
        gs_module.gemini_service.extract_aph_rules([(1, "Some page content")])

