"""Initial schema — all 17 tables, triggers, and reference data.

Revision ID: 0001
Revises:
Create Date: 2026-11-01
"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from alembic import op

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _uuid_pk() -> sa.Column:
    """UUID primary key with server-side gen_random_uuid()."""
    return sa.Column(
        "id",
        postgresql.UUID(as_uuid=False),
        primary_key=True,
        server_default=sa.text("gen_random_uuid()"),
        nullable=False,
    )


def _timestamps() -> list[sa.Column]:
    """created_at / updated_at columns added to every table."""
    return [
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    ]


# ---------------------------------------------------------------------------
# upgrade
# ---------------------------------------------------------------------------

def upgrade() -> None:

    # ── 1. roles ─────────────────────────────────────────────────────────────
    op.create_table(
        "roles",
        _uuid_pk(),
        sa.Column("name", sa.String(50), nullable=False),
        *_timestamps(),
    )
    op.create_index("ix_roles_name", "roles", ["name"], unique=True)

    # ── 2. workflow_stages ───────────────────────────────────────────────────
    op.create_table(
        "workflow_stages",
        _uuid_pk(),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("display_order", sa.Integer, nullable=False),
        *_timestamps(),
    )
    op.create_index(
        "ix_workflow_stages_name", "workflow_stages", ["name"], unique=True
    )

    # ── 3. institutions ──────────────────────────────────────────────────────
    op.create_table(
        "institutions",
        _uuid_pk(),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("region", sa.String(100), nullable=False),
        *_timestamps(),
    )
    op.create_index(
        "ix_institutions_name", "institutions", ["name"], unique=True
    )

    # ── 4. users ─────────────────────────────────────────────────────────────
    op.create_table(
        "users",
        _uuid_pk(),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column(
            "role_id",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("roles.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "institution_id",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("institutions.id", ondelete="RESTRICT"),
            nullable=True,
        ),
        sa.Column("region", sa.String(100), nullable=True),
        sa.Column(
            "is_active", sa.Boolean, nullable=False, server_default=sa.text("true")
        ),
        *_timestamps(),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    # ── 5. programmes ────────────────────────────────────────────────────────
    op.create_table(
        "programmes",
        _uuid_pk(),
        sa.Column(
            "institution_id",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("institutions.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        *_timestamps(),
    )

    # ── 6. aph_versions ──────────────────────────────────────────────────────
    op.create_table(
        "aph_versions",
        _uuid_pk(),
        sa.Column("version_label", sa.String(100), nullable=False),
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            server_default=sa.text("'draft'"),
        ),
        sa.Column(
            "created_by",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        *_timestamps(),
    )

    # ── 7. aph_rules ─────────────────────────────────────────────────────────
    op.create_table(
        "aph_rules",
        _uuid_pk(),
        sa.Column(
            "aph_version_id",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("aph_versions.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("programme", sa.String(255), nullable=False),
        sa.Column("category", sa.String(255), nullable=False),
        sa.Column("parameter", sa.String(255), nullable=False),
        sa.Column("operator", sa.String(20), nullable=False),
        sa.Column("value", sa.String(255), nullable=False),
        sa.Column("unit", sa.String(50), nullable=True),
        sa.Column("source_page", sa.Integer, nullable=True),
        *_timestamps(),
    )

    # ── 8. infrastructure_records ─────────────────────────────────────────────
    op.create_table(
        "infrastructure_records",
        _uuid_pk(),
        sa.Column(
            "institution_id",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("institutions.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("parameter", sa.String(255), nullable=False),
        sa.Column("value", sa.String(255), nullable=False),
        *_timestamps(),
    )

    # ── 9. applications ───────────────────────────────────────────────────────
    op.create_table(
        "applications",
        _uuid_pk(),
        sa.Column(
            "institution_id",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("institutions.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "aph_version_id",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("aph_versions.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "current_stage",
            sa.String(50),
            nullable=False,
            server_default=sa.text("'submission'"),
        ),
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            server_default=sa.text("'draft'"),
        ),
        sa.Column(
            "submitted_by",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        *_timestamps(),
    )

    # ── 10. application_history  (APPEND-ONLY) ────────────────────────────────
    op.create_table(
        "application_history",
        _uuid_pk(),
        sa.Column(
            "application_id",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("applications.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("from_stage", sa.String(50), nullable=True),
        sa.Column("to_stage", sa.String(50), nullable=False),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column(
            "actor_id",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("note", sa.Text, nullable=True),
        *_timestamps(),
    )

    # ── 11. documents ─────────────────────────────────────────────────────────
    op.create_table(
        "documents",
        _uuid_pk(),
        sa.Column(
            "application_id",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("applications.id", ondelete="RESTRICT"),
            nullable=True,
        ),
        sa.Column(
            "uploaded_by",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("file_key", sa.String(500), nullable=False),
        sa.Column("file_name", sa.String(255), nullable=False),
        *_timestamps(),
    )

    # ── 12. evc_assignments ───────────────────────────────────────────────────
    op.create_table(
        "evc_assignments",
        _uuid_pk(),
        sa.Column(
            "application_id",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("applications.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "evc_member_id",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "assigned_by",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        *_timestamps(),
    )

    # ── 13. inspection_checklists ─────────────────────────────────────────────
    op.create_table(
        "inspection_checklists",
        _uuid_pk(),
        sa.Column(
            "evc_assignment_id",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("evc_assignments.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        *_timestamps(),
    )

    # ── 14. inspection_reports ────────────────────────────────────────────────
    op.create_table(
        "inspection_reports",
        _uuid_pk(),
        sa.Column(
            "evc_assignment_id",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("evc_assignments.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "submitted_by",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        *_timestamps(),
    )

    # ── 15. compliance_items ──────────────────────────────────────────────────
    op.create_table(
        "compliance_items",
        _uuid_pk(),
        sa.Column(
            "application_id",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("applications.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("description", sa.String(500), nullable=False),
        sa.Column("due_date", sa.Date, nullable=False),
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            server_default=sa.text("'pending'"),
        ),
        *_timestamps(),
    )

    # ── 16. alerts ────────────────────────────────────────────────────────────
    op.create_table(
        "alerts",
        _uuid_pk(),
        sa.Column(
            "compliance_item_id",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("compliance_items.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "recipient_id",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("message", sa.String(500), nullable=False),
        sa.Column(
            "is_read", sa.Boolean, nullable=False, server_default=sa.text("false")
        ),
        *_timestamps(),
    )

    # ── 17. audit_log  (APPEND-ONLY) ─────────────────────────────────────────
    op.create_table(
        "audit_log",
        _uuid_pk(),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=True,
        ),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("entity_type", sa.String(100), nullable=True),
        sa.Column("entity_id", postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column("detail", sa.Text, nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
        *_timestamps(),
    )

    # =========================================================================
    # Trigger functions
    # =========================================================================

    # ── set_updated_at — installed on every table except the two append-only ones
    op.execute("""
        CREATE OR REPLACE FUNCTION set_updated_at()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = now();
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)

    _updated_at_tables = [
        "roles",
        "workflow_stages",
        "institutions",
        "users",
        "programmes",
        "aph_versions",
        "aph_rules",
        "infrastructure_records",
        "applications",
        "documents",
        "evc_assignments",
        "inspection_checklists",
        "inspection_reports",
        "compliance_items",
        "alerts",
    ]
    for tbl in _updated_at_tables:
        op.execute(f"""
            CREATE TRIGGER trg_{tbl}_updated_at
                BEFORE UPDATE ON {tbl}
                FOR EACH ROW EXECUTE FUNCTION set_updated_at();
        """)

    # ── prevent_mutation — enforces append-only on two tables
    op.execute("""
        CREATE OR REPLACE FUNCTION prevent_mutation()
        RETURNS TRIGGER AS $$
        BEGIN
            RAISE EXCEPTION '% is append-only: UPDATE, DELETE and TRUNCATE are not permitted',
                TG_TABLE_NAME;
        END;
        $$ LANGUAGE plpgsql;
    """)

    # FOR EACH ROW covers UPDATE and DELETE; FOR EACH STATEMENT covers TRUNCATE.
    for tbl in ("application_history", "audit_log"):
        op.execute(f"""
            CREATE TRIGGER {tbl}_immutable_row
                BEFORE UPDATE OR DELETE ON {tbl}
                FOR EACH ROW EXECUTE FUNCTION prevent_mutation();
        """)
        op.execute(f"""
            CREATE TRIGGER {tbl}_immutable_stmt
                BEFORE TRUNCATE ON {tbl}
                FOR EACH STATEMENT EXECUTE FUNCTION prevent_mutation();
        """)

    # =========================================================================
    # Reference data — seeded inline so migrations are self-contained
    # =========================================================================

    # Roles (6)
    op.execute("""
        INSERT INTO roles (id, name, created_at, updated_at) VALUES
            (gen_random_uuid(), 'college_admin',       now(), now()),
            (gen_random_uuid(), 'main_admin',          now(), now()),
            (gen_random_uuid(), 'regional_officer',    now(), now()),
            (gen_random_uuid(), 'bureau_officer',      now(), now()),
            (gen_random_uuid(), 'evc_member',          now(), now()),
            (gen_random_uuid(), 'competent_authority', now(), now())
        ON CONFLICT (name) DO NOTHING;
    """)

    # Workflow stages (6) — ordered per context.md §8
    op.execute("""
        INSERT INTO workflow_stages (id, name, display_order, created_at, updated_at) VALUES
            (gen_random_uuid(), 'Submission',      1, now(), now()),
            (gen_random_uuid(), 'Scrutiny',        2, now(), now()),
            (gen_random_uuid(), 'Re-scrutiny',     3, now(), now()),
            (gen_random_uuid(), 'EVC Review',      4, now(), now()),
            (gen_random_uuid(), 'SAC/SHC Review',  5, now(), now()),
            (gen_random_uuid(), 'Final Decision',  6, now(), now())
        ON CONFLICT (name) DO NOTHING;
    """)


# ---------------------------------------------------------------------------
# downgrade
# ---------------------------------------------------------------------------

def downgrade() -> None:

    # Drop triggers first (order doesn't matter for triggers, but be explicit)
    for tbl in ("application_history", "audit_log"):
        op.execute(f"DROP TRIGGER IF EXISTS {tbl}_immutable_stmt ON {tbl};")
        op.execute(f"DROP TRIGGER IF EXISTS {tbl}_immutable_row ON {tbl};")

    _updated_at_tables = [
        "roles", "workflow_stages", "institutions", "users", "programmes",
        "aph_versions", "aph_rules", "infrastructure_records", "applications",
        "documents", "evc_assignments", "inspection_checklists",
        "inspection_reports", "compliance_items", "alerts",
    ]
    for tbl in _updated_at_tables:
        op.execute(f"DROP TRIGGER IF EXISTS trg_{tbl}_updated_at ON {tbl};")

    op.execute("DROP FUNCTION IF EXISTS prevent_mutation();")
    op.execute("DROP FUNCTION IF EXISTS set_updated_at();")

    # Drop tables in reverse dependency order
    op.drop_table("alerts")
    op.drop_table("compliance_items")
    op.drop_table("inspection_reports")
    op.drop_table("inspection_checklists")
    op.drop_table("evc_assignments")
    op.drop_table("documents")
    op.drop_table("application_history")
    op.drop_table("applications")
    op.drop_table("infrastructure_records")
    op.drop_table("aph_rules")
    op.drop_table("aph_versions")
    op.drop_table("programmes")
    op.drop_table("audit_log")
    op.drop_table("users")
    op.drop_table("institutions")
    op.drop_table("workflow_stages")
    op.drop_table("roles")
