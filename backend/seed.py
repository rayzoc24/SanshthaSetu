"""
seed.py — Create demo data for SanshthaSetu.

Run from the backend/ directory after `alembic upgrade head`:
    python seed.py

Requires DATABASE_URL in the environment (or a .env file in backend/).

What it creates
───────────────
  3 institutions (one per region)
  8 users (3 college_admin + 1 per remaining role)

Roles and workflow_stages are NOT created here — they are inserted by the
Alembic migration (0001_initial_schema) and must already exist.

Idempotency
───────────
Every INSERT uses ON CONFLICT ... DO NOTHING via SQLAlchemy merge logic:
if a row with the same unique key already exists it is skipped.
Running this script twice produces no duplicates.
"""

from __future__ import annotations

import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Load .env if present (so DATABASE_URL is available without exporting it).
# ---------------------------------------------------------------------------
_env_file = Path(__file__).parent / ".env"
if _env_file.exists():
    for line in _env_file.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.strip())

# ---------------------------------------------------------------------------
# Imports (after env is loaded so pydantic-settings resolves DATABASE_URL).
# ---------------------------------------------------------------------------
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.models import Institution, Role, User
from app.services.auth_service import hash_password

DATABASE_URL = os.environ.get("DATABASE_URL", "")
if not DATABASE_URL:
    print("ERROR: DATABASE_URL environment variable is not set.", file=sys.stderr)
    sys.exit(1)

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, expire_on_commit=False)

_NOW = datetime.now(tz=timezone.utc)
_PASSWORD = "Demo@1234"


# ---------------------------------------------------------------------------
# Seed data definitions
# ---------------------------------------------------------------------------

_INSTITUTIONS = [
    {"name": "Alpha Engineering College",    "region": "North"},
    {"name": "Beta Polytechnic Institute",   "region": "South"},
    {"name": "Gamma College of Technology",  "region": "West"},
]

# (email, role_name, region, institution_name | None)
_USERS = [
    ("college_admin_north@example.com", "college_admin",       "North", "Alpha Engineering College"),
    ("college_admin_south@example.com", "college_admin",       "South", "Beta Polytechnic Institute"),
    ("college_admin_west@example.com",  "college_admin",       "West",  "Gamma College of Technology"),
    ("main_admin@example.com",          "main_admin",          None,    None),
    ("regional_officer@example.com",    "regional_officer",    "North", None),
    ("bureau_officer@example.com",      "bureau_officer",      None,    None),
    ("evc_member@example.com",          "evc_member",          None,    None),
    ("competent_authority@example.com", "competent_authority", None,    None),
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _upsert_institution(db, name: str, region: str) -> Institution:
    """Insert institution if it doesn't exist; return the row."""
    existing = db.execute(
        select(Institution).where(Institution.name == name)
    ).scalar_one_or_none()
    if existing:
        return existing
    inst = Institution(
        id=uuid.uuid4(),
        name=name,
        region=region,
        created_at=_NOW,
        updated_at=_NOW,
    )
    db.add(inst)
    db.flush()  # assigns PK so we can reference it immediately
    return inst


def _upsert_user(
    db,
    email: str,
    role: Role,
    institution: Institution | None,
    region: str | None,
) -> User:
    """Insert user if email doesn't exist; return the row."""
    existing = db.execute(
        select(User).where(User.email == email)
    ).scalar_one_or_none()
    if existing:
        return existing
    user = User(
        id=uuid.uuid4(),
        email=email,
        full_name=_make_full_name(email, role.name),
        password_hash=hash_password(_PASSWORD),
        role_id=role.id,
        institution_id=institution.id if institution else None,
        region=region,
        is_active=True,
        created_at=_NOW,
        updated_at=_NOW,
    )
    db.add(user)
    db.flush()
    return user


def _make_full_name(email: str, role_name: str) -> str:
    """Derive a readable display name from the email local part."""
    local = email.split("@")[0]
    return local.replace("_", " ").title()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def seed() -> None:
    with SessionLocal() as db:
        # 1. Verify roles exist (inserted by migration).
        role_rows = db.execute(select(Role)).scalars().all()
        if not role_rows:
            print(
                "ERROR: No roles found in the database.\n"
                "       Run 'alembic upgrade head' first — roles are seeded by the migration.",
                file=sys.stderr,
            )
            sys.exit(1)

        roles: dict[str, Role] = {r.name: r for r in role_rows}

        # 2. Upsert institutions.
        institutions: dict[str, Institution] = {}
        for inst_data in _INSTITUTIONS:
            inst = _upsert_institution(db, inst_data["name"], inst_data["region"])
            institutions[inst_data["name"]] = inst

        # 3. Upsert users.
        users: list[User] = []
        for email, role_name, region, inst_name in _USERS:
            if role_name not in roles:
                print(f"WARNING: role '{role_name}' not found — skipping {email}", file=sys.stderr)
                continue
            institution = institutions.get(inst_name) if inst_name else None
            user = _upsert_user(db, email, roles[role_name], institution, region)
            users.append(user)

        db.commit()

    # 4. Print credentials summary.
    _print_summary()


def _print_summary() -> None:
    col_w = 45
    print()
    print("─" * 60)
    print("  Seed complete — demo credentials")
    print("─" * 60)
    header = f"  {'Email':<{col_w}}  Password"
    print(header)
    print("  " + "─" * (len(header) - 2))
    for email, *_ in _USERS:
        print(f"  {email:<{col_w}}  {_PASSWORD}")
    print("─" * 60)
    print()


if __name__ == "__main__":
    seed()
