"""
seed_aph_demo.py — Seed an authoritative published APH handbook and normative rules.
Guarantees the demo works offline and deterministically without live Gemini API dependencies.
Idempotent: safe to run multiple times without duplicates.
"""

from __future__ import annotations

import os
import sys
import uuid
from datetime import date, datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

env_path = Path(__file__).resolve().parent / ".env"
if env_path.exists():
    load_dotenv(env_path)

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.models import AphPage, AphRule, AphVersion, User

DATABASE_URL = os.environ.get("DATABASE_URL", "")
if not DATABASE_URL:
    print("ERROR: DATABASE_URL is not set.", file=sys.stderr)
    sys.exit(1)

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

DEMO_RULES = [
    {
        "programme": "Engineering & Technology",
        "programme_key": "engineering_technology",
        "category": "Instructional Area",
        "parameter": "Classroom Carpet Area",
        "parameter_key": "classroom_area_degree",
        "operator": ">=",
        "numeric_value": 66.0,
        "string_value": None,
        "unit": "sq_m",
        "source_page": 24,
        "source_quote": "Classroom carpet area requirement for Under Graduate technical degree programmes shall be a minimum of 66 sq.m per room.",
    },
    {
        "programme": "Engineering & Technology",
        "programme_key": "engineering_technology",
        "category": "Instructional Area",
        "parameter": "Number of Classrooms",
        "parameter_key": "classroom_count_degree",
        "operator": ">=",
        "numeric_value": 4.0,
        "string_value": None,
        "unit": "count",
        "source_page": 24,
        "source_quote": "Minimum number of classrooms required for initial approved intake of 60 students is 4 rooms.",
    },
    {
        "programme": "Engineering & Technology",
        "programme_key": "engineering_technology",
        "category": "Instructional Area",
        "parameter": "Tutorial Room Carpet Area",
        "parameter_key": "tutorial_room_area",
        "operator": ">=",
        "numeric_value": 33.0,
        "string_value": None,
        "unit": "sq_m",
        "source_page": 25,
        "source_quote": "Tutorial rooms shall have a minimum carpet area of 33 sq.m per room.",
    },
    {
        "programme": "Engineering & Technology",
        "programme_key": "engineering_technology",
        "category": "Instructional Area",
        "parameter": "Laboratory Carpet Area",
        "parameter_key": "laboratory_area_engineering",
        "operator": ">=",
        "numeric_value": 66.0,
        "string_value": None,
        "unit": "sq_m",
        "source_page": 26,
        "source_quote": "Engineering and Technology laboratories must provide at least 66 sq.m of carpet area per laboratory unit.",
    },
    {
        "programme": "Engineering & Technology",
        "programme_key": "engineering_technology",
        "category": "Instructional Area",
        "parameter": "Computer Center Carpet Area",
        "parameter_key": "computer_center_area",
        "operator": ">=",
        "numeric_value": 150.0,
        "string_value": None,
        "unit": "sq_m",
        "source_page": 27,
        "source_quote": "Central Computer Center requirement for technical institutions is 150 sq.m carpet area.",
    },
    {
        "programme": "Engineering & Technology",
        "programme_key": "engineering_technology",
        "category": "Instructional Area",
        "parameter": "Central Library and Reading Room Area",
        "parameter_key": "library_reading_room_area",
        "operator": ">=",
        "numeric_value": 400.0,
        "string_value": None,
        "unit": "sq_m",
        "source_page": 28,
        "source_quote": "Central Library inclusive of Reading Room shall have a minimum carpet area of 400 sq.m.",
    },
    {
        "programme": "Engineering & Technology",
        "programme_key": "engineering_technology",
        "category": "Administrative Area",
        "parameter": "Principal / Director Office Carpet Area",
        "parameter_key": "principal_office_area",
        "operator": ">=",
        "numeric_value": 30.0,
        "string_value": None,
        "unit": "sq_m",
        "source_page": 30,
        "source_quote": "Carpet area for Principal / Director office shall be at least 30 sq.m.",
    },
    {
        "programme": "Engineering & Technology",
        "programme_key": "engineering_technology",
        "category": "Amenities Area",
        "parameter": "Cafeteria / Canteen Area",
        "parameter_key": "student_canteen_area",
        "operator": ">=",
        "numeric_value": 150.0,
        "string_value": None,
        "unit": "sq_m",
        "source_page": 32,
        "source_quote": "Cafeteria / Student Canteen shall be provided with minimum 150 sq.m carpet area.",
    },
    {
        "programme": "Engineering & Technology",
        "programme_key": "engineering_technology",
        "category": "Faculty",
        "parameter": "Faculty to Student Cadre Ratio",
        "parameter_key": "faculty_student_ratio_ug",
        "operator": "<=",
        "numeric_value": 20.0,
        "string_value": None,
        "unit": "ratio",
        "source_page": 38,
        "source_quote": "For Under Graduate Degree Engineering, the Faculty to Student ratio shall not exceed 1:20.",
    },
    {
        "programme": "Engineering & Technology",
        "programme_key": "engineering_technology",
        "category": "Statutory & Safety",
        "parameter": "Fire Safety Certificate",
        "parameter_key": "fire_safety_certificate",
        "operator": "==",
        "numeric_value": None,
        "string_value": "valid",
        "unit": "status",
        "source_page": 44,
        "source_quote": "A valid Fire Safety Certificate issued by the Competent Government Authority is mandatory.",
    },
]


def seed_aph_demo():
    with SessionLocal() as db:
        admin_user = (
            db.execute(select(User).where(User.email == "main_admin@example.com"))
            .scalars()
            .first()
        )
        if not admin_user:
            print("ERROR: main_admin@example.com not found. Run seed.py first.", file=sys.stderr)
            sys.exit(1)

        version_label = "APH Norms 2026-27 (Official Reference)"
        existing_version = (
            db.execute(select(AphVersion).where(AphVersion.version_label == version_label))
            .scalars()
            .first()
        )

        if existing_version:
            print(f"Version '{version_label}' already exists. Updating rules if needed.")
            version = existing_version
        else:
            version = AphVersion(
                id=uuid.uuid4(),
                version_label=version_label,
                file_name="AICTE_APH_2026_27_Official.pdf",
                file_key="aph/demo/AICTE_APH_2026_27_Official.pdf",
                status="published",
                extraction_status="done",
                content_hash="demo_aph_hash_2026_canonical",
                effective_date=date.today(),
                published_at=datetime.now(timezone.utc),
                published_by=admin_user.id,
                created_by=admin_user.id,
                notes="Canonically published normative ruleset for hackathon demonstration.",
            )
            db.add(version)
            db.flush()

        for rule_data in DEMO_RULES:
            existing_rule = db.execute(
                select(AphRule).where(
                    AphRule.aph_version_id == version.id,
                    AphRule.programme_key == rule_data["programme_key"],
                    AphRule.parameter_key == rule_data["parameter_key"],
                )
            ).scalar_one_or_none()

            if not existing_rule:
                rule = AphRule(
                    id=uuid.uuid4(),
                    aph_version_id=version.id,
                    programme=rule_data["programme"],
                    programme_key=rule_data["programme_key"],
                    category=rule_data["category"],
                    parameter=rule_data["parameter"],
                    parameter_key=rule_data["parameter_key"],
                    operator=rule_data["operator"],
                    numeric_value=rule_data["numeric_value"],
                    string_value=rule_data["string_value"],
                    unit=rule_data["unit"],
                    source_page=rule_data["source_page"],
                    source_quote=rule_data["source_quote"],
                    needs_review=False,
                    is_ai_suggested=False,
                    edited_by=admin_user.id,
                    edited_at=datetime.now(timezone.utc),
                )
                db.add(rule)

        db.commit()
        print(f"Successfully seeded '{version_label}' with {len(DEMO_RULES)} published rules!")


if __name__ == "__main__":
    seed_aph_demo()

