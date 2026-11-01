"""APH Pipeline — extends aph_versions, aph_rules, creates aph_pages

Revision ID: 0002
Revises: 0001
Create Date: 2026-11-01
"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from alembic import op

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── 1. aph_versions (add new columns only) ──────────────────────────────
    op.add_column("aph_versions", sa.Column("file_key", sa.Text(), nullable=True))
    op.add_column("aph_versions", sa.Column("file_name", sa.Text(), nullable=True))
    op.add_column("aph_versions", sa.Column("published_at", sa.TIMESTAMP(timezone=True), nullable=True))
    op.add_column(
        "aph_versions",
        sa.Column(
            "published_by",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=True,
        ),
    )
    op.add_column("aph_versions", sa.Column("effective_date", sa.Date(), nullable=True))
    op.add_column(
        "aph_versions",
        sa.Column("extraction_status", sa.Text(), nullable=False, server_default=sa.text("'none'")),
    )
    op.add_column("aph_versions", sa.Column("content_hash", sa.Text(), nullable=True))
    op.add_column("aph_versions", sa.Column("extraction_log", postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column("aph_versions", sa.Column("notes", sa.Text(), nullable=True))

    # ── 2. aph_pages (new table) ─────────────────────────────────────────────
    op.create_table(
        "aph_pages",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=False),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "version_id",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("aph_versions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("page_no", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
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
        sa.UniqueConstraint("version_id", "page_no", name="uq_aph_pages_version_page"),
    )

    # Attach trigger for set_updated_at on aph_pages
    op.execute("""
        CREATE TRIGGER trg_aph_pages_updated_at
            BEFORE UPDATE ON aph_pages
            FOR EACH ROW EXECUTE FUNCTION set_updated_at();
    """)

    # ── 3. aph_rules (drop value, add new columns & unique constraint) ──────
    op.drop_column("aph_rules", "value")
    op.add_column("aph_rules", sa.Column("parameter_key", sa.Text(), nullable=False))
    op.add_column("aph_rules", sa.Column("programme_key", sa.Text(), nullable=False))
    op.add_column("aph_rules", sa.Column("string_value", sa.Text(), nullable=True))
    op.add_column("aph_rules", sa.Column("numeric_value", sa.Numeric(), nullable=True))
    op.add_column("aph_rules", sa.Column("source_quote", sa.Text(), nullable=True))
    op.add_column(
        "aph_rules",
        sa.Column("needs_review", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.add_column(
        "aph_rules",
        sa.Column("is_ai_suggested", sa.Boolean(), nullable=False, server_default=sa.text("true")),
    )
    op.add_column(
        "aph_rules",
        sa.Column(
            "edited_by",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=True,
        ),
    )
    op.add_column("aph_rules", sa.Column("edited_at", sa.TIMESTAMP(timezone=True), nullable=True))

    op.create_unique_constraint(
        "uq_aph_rules_version_prog_param",
        "aph_rules",
        ["aph_version_id", "programme_key", "parameter_key"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_aph_rules_version_prog_param", "aph_rules", type_="unique")
    op.drop_column("aph_rules", "edited_at")
    op.drop_column("aph_rules", "edited_by")
    op.drop_column("aph_rules", "is_ai_suggested")
    op.drop_column("aph_rules", "needs_review")
    op.drop_column("aph_rules", "source_quote")
    op.drop_column("aph_rules", "numeric_value")
    op.drop_column("aph_rules", "string_value")
    op.drop_column("aph_rules", "programme_key")
    op.drop_column("aph_rules", "parameter_key")
    op.add_column("aph_rules", sa.Column("value", sa.String(255), nullable=False))

    op.execute("DROP TRIGGER IF EXISTS trg_aph_pages_updated_at ON aph_pages;")
    op.drop_table("aph_pages")

    op.drop_column("aph_versions", "notes")
    op.drop_column("aph_versions", "extraction_log")
    op.drop_column("aph_versions", "content_hash")
    op.drop_column("aph_versions", "extraction_status")
    op.drop_column("aph_versions", "effective_date")
    op.drop_column("aph_versions", "published_by")
    op.drop_column("aph_versions", "published_at")
    op.drop_column("aph_versions", "file_name")
    op.drop_column("aph_versions", "file_key")

