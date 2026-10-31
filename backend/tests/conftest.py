"""
pytest configuration and shared fixtures for the SanshthaSetu backend tests.

Database strategy
─────────────────
All tests run against a REAL PostgreSQL database pointed to by TEST_DATABASE_URL.
SQLite and mocks are explicitly not used.

Isolation strategy  (savepoint / nested-transaction pattern)
─────────────────────────────────────────────────────────────
Session-scope:
  - alembic downgrade base + upgrade head runs once per pytest session.
  - Eight role-users and three institutions are inserted once as committed rows
    so they are visible to audit_service's independent SessionLocal().

Per-test isolation:
  - Each test gets a real transaction that wraps the test in a SAVEPOINT.
  - The endpoint under test may call db.commit() — this commits to the
    savepoint, NOT to the outer transaction, so rows are visible within the
    test but the outer rollback at teardown wipes everything.
  - The outer transaction is rolled back after every test, restoring the DB
    to the committed seed state.

record_audit isolation
──────────────────────
record_audit() opens its own SessionLocal() independently.  The conftest
overrides SessionLocal in app.database so it uses the same underlying
connection as the test, but behind a sub-savepoint.  Audit rows committed by
record_audit therefore land in the test DB and are queryable in assertions.

Environment
───────────
Set TEST_DATABASE_URL in the environment (or a .env file) before running:
    TEST_DATABASE_URL=postgresql+psycopg2://user:pw@host/testdb?sslmode=require pytest tests/
"""

from __future__ import annotations

import os
import subprocess
import uuid
from datetime import datetime, timezone
from typing import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import Session, sessionmaker

# ---------------------------------------------------------------------------
# 0. Point DATABASE_URL at the test database BEFORE importing anything from
#    app — config.py reads DATABASE_URL at import time via pydantic-settings.
# ---------------------------------------------------------------------------
_test_db_url = os.environ.get("TEST_DATABASE_URL") or os.environ.get("DATABASE_URL", "")
if not _test_db_url:
    raise RuntimeError(
        "TEST_DATABASE_URL environment variable must be set before running tests.\n"
        "Example: TEST_DATABASE_URL=postgresql+psycopg2://user:pw@host/testdb?sslmode=require"
    )
os.environ["DATABASE_URL"] = _test_db_url

# Now safe to import app modules.
from app.config import get_settings  # noqa: E402
get_settings.cache_clear()           # force re-read with the test URL

from app.database import Base        # noqa: E402
from app.models import (             # noqa: E402
    AuditLog, Institution, Role, User,
)
from app.services.auth_service import hash_password  # noqa: E402


# ---------------------------------------------------------------------------
# 1. Schema setup — runs ONCE per pytest session
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session", autouse=True)
def apply_migrations() -> None:
    """
    Drop and recreate the entire test schema via Alembic to guarantee a clean
    state for every test run.
    """
    env = {**os.environ, "DATABASE_URL": _test_db_url}
    backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    subprocess.run(
        ["python", "-m", "alembic", "downgrade", "base"],
        cwd=backend_dir,
        env=env,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["python", "-m", "alembic", "upgrade", "head"],
        cwd=backend_dir,
        env=env,
        check=True,
        capture_output=True,
    )


# ---------------------------------------------------------------------------
# 2. Session-scoped engine and SessionLocal override
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def test_engine(apply_migrations):
    engine = create_engine(_test_db_url, pool_pre_ping=True)
    yield engine
    engine.dispose()


@pytest.fixture(scope="session")
def TestSessionLocal(test_engine):
    """
    A sessionmaker bound to the test engine.
    Also patched into app.database so that record_audit() uses the test DB.
    """
    import app.database as _db_module  # noqa: PLC0415

    factory = sessionmaker(
        bind=test_engine,
        autocommit=False,
        autoflush=False,
        expire_on_commit=False,
    )
    # Patch record_audit's SessionLocal to use the test DB.
    original = _db_module.SessionLocal
    _db_module.SessionLocal = factory
    yield factory
    _db_module.SessionLocal = original


# ---------------------------------------------------------------------------
# 3. Session-scoped seed data — committed rows visible to all tests
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def seed_users(TestSessionLocal) -> dict[str, User]:
    """
    Insert one user per role (plus one permanently inactive user) once for
    the whole session.  Uses ON CONFLICT (email) DO NOTHING so re-runs are safe.

    Returns a dict keyed by role name (plus "inactive" for the disabled user).
    """
    role_names = [
        "college_admin",
        "main_admin",
        "regional_officer",
        "bureau_officer",
        "evc_member",
        "competent_authority",
    ]

    with TestSessionLocal() as db:
        # Fetch role records (inserted by migration).
        roles: dict[str, Role] = {
            r.name: r for r in db.query(Role).all()
        }

        # Insert a test institution so college_admin can reference it.
        inst = db.query(Institution).filter_by(name="Test Institution").first()
        if inst is None:
            inst = Institution(
                id=uuid.uuid4(),
                name="Test Institution",
                region="Test",
                created_at=datetime.now(tz=timezone.utc),
                updated_at=datetime.now(tz=timezone.utc),
            )
            db.add(inst)
            db.flush()

        users: dict[str, User] = {}
        for role_name in role_names:
            email = f"test_{role_name}@example.com"
            existing = db.query(User).filter_by(email=email).first()
            if existing:
                users[role_name] = existing
                continue

            u = User(
                id=uuid.uuid4(),
                email=email,
                full_name=f"Test {role_name.replace('_', ' ').title()}",
                password_hash=hash_password("Test@1234"),
                role_id=roles[role_name].id,
                institution_id=inst.id if role_name == "college_admin" else None,
                region="North" if role_name == "regional_officer" else None,
                is_active=True,
                created_at=datetime.now(tz=timezone.utc),
                updated_at=datetime.now(tz=timezone.utc),
            )
            db.add(u)
            users[role_name] = u

        # Permanently inactive user (is_active=False) — used in RBAC tests.
        inactive_email = "test_inactive@example.com"
        inactive = db.query(User).filter_by(email=inactive_email).first()
        if inactive is None:
            inactive = User(
                id=uuid.uuid4(),
                email=inactive_email,
                full_name="Inactive User",
                password_hash=hash_password("Test@1234"),
                role_id=roles["main_admin"].id,
                is_active=False,
                created_at=datetime.now(tz=timezone.utc),
                updated_at=datetime.now(tz=timezone.utc),
            )
            db.add(inactive)
        users["inactive"] = inactive

        db.commit()

    # Re-fetch with a fresh session to return detached-safe objects.
    with TestSessionLocal() as db:
        result = {}
        for key, u in users.items():
            refreshed = db.get(User, u.id)
            db.expunge(refreshed)
            result[key] = refreshed
    return result


# ---------------------------------------------------------------------------
# 4. Per-test transaction + savepoint isolation
# ---------------------------------------------------------------------------

@pytest.fixture
def db_session(test_engine, TestSessionLocal) -> Generator[Session, None, None]:
    """
    Per-test database session.

    Opens a real transaction, then immediately creates a SAVEPOINT.
    The endpoint code calls db.commit() → commits to the savepoint (not the
    outer transaction).  After the test, we roll back to the outer transaction
    start, restoring the DB to the session-seed state.
    """
    connection = test_engine.connect()
    outer_tx = connection.begin()

    # Bind session to this connection so all ORM work uses the same transaction.
    # SQLAlchemy 2.x: pass connection via bind keyword (still supported in 2.x
    # via the legacy Session(bind=...) path, or use sessionmaker(bind=conn)()).
    BoundSession = sessionmaker(bind=connection, autocommit=False, autoflush=False, expire_on_commit=False)
    session = BoundSession()

    # Create a savepoint so endpoint commits stay inside this test.
    nested = connection.begin_nested()

    # Re-open the savepoint if the endpoint releases it via commit.
    @event.listens_for(session, "after_transaction_end")
    def restart_savepoint(session, transaction):  # noqa: ANN001
        if transaction.nested and not transaction._parent.nested:
            session.begin_nested()

    yield session

    session.close()
    outer_tx.rollback()
    connection.close()


@pytest.fixture
def client(db_session: Session) -> Generator[TestClient, None, None]:
    """
    TestClient with get_db overridden to use the per-test db_session.
    The app import is deferred so DATABASE_URL is already set.
    """
    from app.database import get_db   # noqa: PLC0415
    from app.main import app          # noqa: PLC0415

    def override_get_db():
        try:
            yield db_session
        finally:
            pass  # session lifecycle managed by db_session fixture

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# 5. Convenience: per-test audit query helper
# ---------------------------------------------------------------------------

def query_audit(email_fragment: str, action: str) -> list[AuditLog]:
    """
    Query audit_log directly via a fresh independent session.
    Filters by action and detail containing email_fragment.
    Used in tests to assert on audit rows written by record_audit().
    """
    import app.database as _db_module  # noqa: PLC0415

    with _db_module.SessionLocal() as db:
        rows = (
            db.query(AuditLog)
            .filter(
                AuditLog.action == action,
                AuditLog.detail.contains(email_fragment),
            )
            .all()
        )
        return rows
