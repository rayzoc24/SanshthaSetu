"""
All 17 ORM models for SanshthaSetu.

Creation order mirrors the migration dependency order:
  roles → institutions → users → programmes / aph_versions → aph_rules →
  infrastructure_records → workflow_stages → applications →
  application_history → documents → evc_assignments →
  inspection_checklists → inspection_reports →
  compliance_items → alerts → audit_log

Circular FK note
───────────────
users.institution_id → institutions.id
institutions has no FK back to users.
SQLAlchemy resolves this because Institution is declared before User;
the FK string "institutions.id" is resolved lazily by the mapper.

Append-only tables
──────────────────
application_history and audit_log: never issue UPDATE or DELETE from Python.
Database-level triggers (installed in the migration) enforce this and will
raise an exception if the constraint is violated.
"""

import uuid
from datetime import date, datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    func,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin


# ---------------------------------------------------------------------------
# 1. Role
# ---------------------------------------------------------------------------
class Role(TimestampMixin, Base):
    __tablename__ = "roles"

    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)

    # Relationships
    users: Mapped[list["User"]] = relationship("User", back_populates="role")

    def __repr__(self) -> str:
        return f"<Role {self.name!r}>"


# ---------------------------------------------------------------------------
# 2. Institution  (declared before User to resolve the circular FK)
# ---------------------------------------------------------------------------
class Institution(TimestampMixin, Base):
    __tablename__ = "institutions"

    __table_args__ = (
        UniqueConstraint("name", name="uq_institutions_name"),
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    region: Mapped[str] = mapped_column(String(100), nullable=False)

    # Relationships
    users: Mapped[list["User"]] = relationship(
        "User",
        back_populates="institution",
        foreign_keys="User.institution_id",
    )
    programmes: Mapped[list["Programme"]] = relationship(
        "Programme", back_populates="institution"
    )
    infrastructure_records: Mapped[list["InfrastructureRecord"]] = relationship(
        "InfrastructureRecord", back_populates="institution"
    )
    applications: Mapped[list["Application"]] = relationship(
        "Application", back_populates="institution"
    )

    def __repr__(self) -> str:
        return f"<Institution {self.name!r}>"


# ---------------------------------------------------------------------------
# 3. User
# ---------------------------------------------------------------------------
class User(TimestampMixin, Base):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)

    role_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("roles.id", ondelete="RESTRICT"),
        nullable=False,
    )
    # Nullable: only college_admin users are linked to an institution.
    institution_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("institutions.id", ondelete="RESTRICT"),
        nullable=True,
    )
    # NULL = no region scope; populated for regional_officer.
    region: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # Relationships
    role: Mapped["Role"] = relationship("Role", back_populates="users")
    institution: Mapped[Optional["Institution"]] = relationship(
        "Institution",
        back_populates="users",
        foreign_keys=[institution_id],
    )

    def __repr__(self) -> str:
        return f"<User {self.email!r}>"


# ---------------------------------------------------------------------------
# 4. Programme  (stub — extended in Module 1)
# ---------------------------------------------------------------------------
class Programme(TimestampMixin, Base):
    __tablename__ = "programmes"

    institution_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("institutions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)

    # Relationships
    institution: Mapped["Institution"] = relationship(
        "Institution", back_populates="programmes"
    )

    def __repr__(self) -> str:
        return f"<Programme {self.name!r}>"


# ---------------------------------------------------------------------------
# 5. AphVersion  (extended in Module 1)
# ---------------------------------------------------------------------------
class AphVersion(TimestampMixin, Base):
    __tablename__ = "aph_versions"

    version_label: Mapped[str] = mapped_column(String(100), nullable=False)
    file_key: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    file_name: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # draft | published
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="draft", server_default="draft"
    )
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    published_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True,
    )
    effective_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    # none | running | done | failed
    extraction_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="none", server_default="none"
    )
    content_hash: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    extraction_log: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )

    # Relationships
    creator: Mapped["User"] = relationship("User", foreign_keys=[created_by])
    publisher: Mapped[Optional["User"]] = relationship("User", foreign_keys=[published_by])
    rules: Mapped[list["AphRule"]] = relationship("AphRule", back_populates="aph_version", cascade="all, delete-orphan")
    pages: Mapped[list["AphPage"]] = relationship("AphPage", back_populates="aph_version", cascade="all, delete-orphan")
    applications: Mapped[list["Application"]] = relationship(
        "Application", back_populates="aph_version"
    )

    def __repr__(self) -> str:
        return f"<AphVersion {self.version_label!r} status={self.status!r}>"


# ---------------------------------------------------------------------------
# 5b. AphPage (new in Module 1)
# ---------------------------------------------------------------------------
class AphPage(TimestampMixin, Base):
    __tablename__ = "aph_pages"

    __table_args__ = (
        UniqueConstraint("version_id", "page_no", name="uq_aph_pages_version_page"),
    )

    version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("aph_versions.id", ondelete="CASCADE"),
        nullable=False,
    )
    page_no: Mapped[int] = mapped_column(Integer, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)

    # Relationships
    aph_version: Mapped["AphVersion"] = relationship("AphVersion", back_populates="pages")

    def __repr__(self) -> str:
        return f"<AphPage v={self.version_id} p={self.page_no}>"


# ---------------------------------------------------------------------------
# 6. AphRule  (extended in Module 1)
# ---------------------------------------------------------------------------
class AphRule(TimestampMixin, Base):
    __tablename__ = "aph_rules"

    __table_args__ = (
        UniqueConstraint("aph_version_id", "programme_key", "parameter_key", name="uq_aph_rules_version_prog_param"),
    )

    aph_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("aph_versions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    programme: Mapped[str] = mapped_column(String(255), nullable=False)
    programme_key: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(String(255), nullable=False)
    parameter: Mapped[str] = mapped_column(String(255), nullable=False)
    parameter_key: Mapped[str] = mapped_column(Text, nullable=False)
    operator: Mapped[str] = mapped_column(String(20), nullable=False)
    string_value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    numeric_value: Mapped[Optional[float]] = mapped_column(Numeric, nullable=True)
    unit: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    source_page: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    source_quote: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    needs_review: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=func.false())
    is_ai_suggested: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=func.true())
    edited_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True,
    )
    edited_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    aph_version: Mapped["AphVersion"] = relationship(
        "AphVersion", back_populates="rules"
    )
    editor: Mapped[Optional["User"]] = relationship("User", foreign_keys=[edited_by])

    def __repr__(self) -> str:
        return f"<AphRule {self.parameter_key!r}>"

# ---------------------------------------------------------------------------
# 7. InfrastructureRecord  (stub — extended in Module 3)
# ---------------------------------------------------------------------------
class InfrastructureRecord(TimestampMixin, Base):
    __tablename__ = "infrastructure_records"

    institution_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("institutions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    parameter: Mapped[str] = mapped_column(String(255), nullable=False)
    value: Mapped[str] = mapped_column(String(255), nullable=False)

    # Relationships
    institution: Mapped["Institution"] = relationship(
        "Institution", back_populates="infrastructure_records"
    )

    def __repr__(self) -> str:
        return f"<InfrastructureRecord {self.parameter!r}>"


# ---------------------------------------------------------------------------
# 8. WorkflowStage  (reference data seeded in migration)
# ---------------------------------------------------------------------------
class WorkflowStage(TimestampMixin, Base):
    __tablename__ = "workflow_stages"

    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    display_order: Mapped[int] = mapped_column(Integer, nullable=False)

    def __repr__(self) -> str:
        return f"<WorkflowStage {self.name!r} order={self.display_order}>"


# ---------------------------------------------------------------------------
# 9. Application  (stub — extended in Module 4)
# ---------------------------------------------------------------------------
class Application(TimestampMixin, Base):
    __tablename__ = "applications"

    institution_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("institutions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    aph_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("aph_versions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    current_stage: Mapped[str] = mapped_column(
        String(50), nullable=False, default="submission", server_default="submission"
    )
    # draft | submitted | under_review | approved | rejected
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="draft", server_default="draft"
    )
    submitted_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )

    # Relationships
    institution: Mapped["Institution"] = relationship(
        "Institution", back_populates="applications"
    )
    aph_version: Mapped["AphVersion"] = relationship(
        "AphVersion", back_populates="applications"
    )
    submitter: Mapped["User"] = relationship("User", foreign_keys=[submitted_by])
    history: Mapped[list["ApplicationHistory"]] = relationship(
        "ApplicationHistory", back_populates="application"
    )
    documents: Mapped[list["Document"]] = relationship(
        "Document", back_populates="application"
    )
    evc_assignments: Mapped[list["EvcAssignment"]] = relationship(
        "EvcAssignment", back_populates="application"
    )
    compliance_items: Mapped[list["ComplianceItem"]] = relationship(
        "ComplianceItem", back_populates="application"
    )

    def __repr__(self) -> str:
        return f"<Application {self.id} stage={self.current_stage!r}>"


# ---------------------------------------------------------------------------
# 10. ApplicationHistory  ⚠️ APPEND-ONLY — never UPDATE or DELETE
# ---------------------------------------------------------------------------
class ApplicationHistory(TimestampMixin, Base):
    __tablename__ = "application_history"

    application_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("applications.id", ondelete="RESTRICT"),
        nullable=False,
    )
    from_stage: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    to_stage: Mapped[str] = mapped_column(String(50), nullable=False)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    actor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    application: Mapped["Application"] = relationship(
        "Application", back_populates="history"
    )
    actor: Mapped["User"] = relationship("User", foreign_keys=[actor_id])

    def __repr__(self) -> str:
        return f"<ApplicationHistory {self.action!r} → {self.to_stage!r}>"


# ---------------------------------------------------------------------------
# 11. Document  (stub — extended in Module 4)
# ---------------------------------------------------------------------------
class Document(TimestampMixin, Base):
    __tablename__ = "documents"

    # Nullable: documents may exist before they are linked to an application.
    application_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("applications.id", ondelete="RESTRICT"),
        nullable=True,
    )
    uploaded_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    # Cloudflare R2 object key
    file_key: Mapped[str] = mapped_column(String(500), nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)

    # Relationships
    application: Mapped[Optional["Application"]] = relationship(
        "Application", back_populates="documents"
    )
    uploader: Mapped["User"] = relationship("User", foreign_keys=[uploaded_by])

    def __repr__(self) -> str:
        return f"<Document {self.file_name!r}>"


# ---------------------------------------------------------------------------
# 12. EvcAssignment  (stub — extended in Module 5)
# ---------------------------------------------------------------------------
class EvcAssignment(TimestampMixin, Base):
    __tablename__ = "evc_assignments"

    application_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("applications.id", ondelete="RESTRICT"),
        nullable=False,
    )
    evc_member_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    assigned_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )

    # Relationships
    application: Mapped["Application"] = relationship(
        "Application", back_populates="evc_assignments"
    )
    evc_member: Mapped["User"] = relationship("User", foreign_keys=[evc_member_id])
    assigner: Mapped["User"] = relationship("User", foreign_keys=[assigned_by])
    checklists: Mapped[list["InspectionChecklist"]] = relationship(
        "InspectionChecklist", back_populates="evc_assignment"
    )
    reports: Mapped[list["InspectionReport"]] = relationship(
        "InspectionReport", back_populates="evc_assignment"
    )

    def __repr__(self) -> str:
        return f"<EvcAssignment app={self.application_id}>"


# ---------------------------------------------------------------------------
# 13. InspectionChecklist  (stub — extended in Module 5)
# ---------------------------------------------------------------------------
class InspectionChecklist(TimestampMixin, Base):
    __tablename__ = "inspection_checklists"

    evc_assignment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("evc_assignments.id", ondelete="RESTRICT"),
        nullable=False,
    )

    # Relationships
    evc_assignment: Mapped["EvcAssignment"] = relationship(
        "EvcAssignment", back_populates="checklists"
    )

    def __repr__(self) -> str:
        return f"<InspectionChecklist {self.id}>"


# ---------------------------------------------------------------------------
# 14. InspectionReport  (stub — extended in Module 5)
# ---------------------------------------------------------------------------
class InspectionReport(TimestampMixin, Base):
    __tablename__ = "inspection_reports"

    evc_assignment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("evc_assignments.id", ondelete="RESTRICT"),
        nullable=False,
    )
    submitted_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )

    # Relationships
    evc_assignment: Mapped["EvcAssignment"] = relationship(
        "EvcAssignment", back_populates="reports"
    )
    submitter: Mapped["User"] = relationship("User", foreign_keys=[submitted_by])

    def __repr__(self) -> str:
        return f"<InspectionReport {self.id}>"


# ---------------------------------------------------------------------------
# 15. ComplianceItem  (stub — extended in Module 6)
# ---------------------------------------------------------------------------
class ComplianceItem(TimestampMixin, Base):
    __tablename__ = "compliance_items"

    application_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("applications.id", ondelete="RESTRICT"),
        nullable=False,
    )
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    due_date: Mapped[date] = mapped_column(Date, nullable=False)
    # pending | submitted | overdue | waived
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending", server_default="pending"
    )

    # Relationships
    application: Mapped["Application"] = relationship(
        "Application", back_populates="compliance_items"
    )
    alerts: Mapped[list["Alert"]] = relationship("Alert", back_populates="compliance_item")

    def __repr__(self) -> str:
        return f"<ComplianceItem {self.description[:40]!r}>"


# ---------------------------------------------------------------------------
# 16. Alert  (stub — extended in Module 6)
# ---------------------------------------------------------------------------
class Alert(TimestampMixin, Base):
    __tablename__ = "alerts"

    compliance_item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("compliance_items.id", ondelete="RESTRICT"),
        nullable=False,
    )
    recipient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    message: Mapped[str] = mapped_column(String(500), nullable=False)
    is_read: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Relationships
    compliance_item: Mapped["ComplianceItem"] = relationship(
        "ComplianceItem", back_populates="alerts"
    )
    recipient: Mapped["User"] = relationship("User", foreign_keys=[recipient_id])

    def __repr__(self) -> str:
        return f"<Alert {self.message[:40]!r} read={self.is_read}>"


# ---------------------------------------------------------------------------
# 17. AuditLog  ⚠️ APPEND-ONLY — never UPDATE or DELETE
# ---------------------------------------------------------------------------
class AuditLog(TimestampMixin, Base):
    __tablename__ = "audit_log"

    # NULL for unauthenticated actions (e.g. failed login before user is known)
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True,
    )
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    entity_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    detail: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)

    # Relationships
    user: Mapped[Optional["User"]] = relationship("User", foreign_keys=[user_id])

    def __repr__(self) -> str:
        return f"<AuditLog action={self.action!r} user={self.user_id}>"
