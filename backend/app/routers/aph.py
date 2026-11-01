"""
APH router endpoints (/aph/...)
Follows unprefixed Module 0 pattern.
Static routes (/versions/published) are mounted before parameterized routes (/versions/{id}).
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from typing import Optional

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import require_roles
from app.models import AphRule, AphVersion, User
from app.schemas.aph import (
    AphPublishRequest,
    AphRuleCreateRequest,
    AphRuleResponse,
    AphRuleUpdateRequest,
    AphVersionResponse,
)
from app.services.aph_service import aph_service
from app.services.audit_service import record_audit
from app.services.storage_service import storage_service

router = APIRouter(prefix="/aph", tags=["aph"])


# ---------------------------------------------------------------------------
# Static Route: Latest Published Version (Any authenticated user)
# Defined before /versions/{id} to prevent path collision
# ---------------------------------------------------------------------------

@router.get(
    "/versions/published",
    response_model=AphVersionResponse,
    summary="Get the active published APH version",
)
def get_published_version(
    _current_user: User = Depends(
        require_roles([
            "college_admin",
            "main_admin",
            "regional_officer",
            "bureau_officer",
            "evc_member",
            "competent_authority",
        ])
    ),
    db: Session = Depends(get_db),
) -> AphVersionResponse:
    today = date.today()
    version = (
        db.execute(
            select(AphVersion)
            .where(
                AphVersion.status == "published",
                AphVersion.effective_date <= today,
            )
            .order_by(AphVersion.effective_date.desc(), AphVersion.published_at.desc())
        )
        .scalars()
        .first()
    )
    if not version:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active published APH version found.",
        )
    return version


# ---------------------------------------------------------------------------
# Version List & Detail Endpoints (main_admin)
# ---------------------------------------------------------------------------

@router.get(
    "/versions",
    response_model=list[AphVersionResponse],
    summary="List all APH versions",
)
def list_versions(
    _admin: User = Depends(require_roles(["main_admin"])),
    db: Session = Depends(get_db),
) -> list[AphVersionResponse]:
    versions = (
        db.execute(select(AphVersion).order_by(AphVersion.created_at.desc()))
        .scalars()
        .all()
    )
    return versions


@router.post(
    "/versions",
    response_model=AphVersionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload APH handbook PDF and create draft version",
)
async def upload_version(
    version_label: str = Form(...),
    file: UploadFile = File(...),
    admin: User = Depends(require_roles(["main_admin"])),
    db: Session = Depends(get_db),
) -> AphVersionResponse:
    file_bytes = await file.read()
    try:
        version = aph_service.upload_aph(
            file_bytes=file_bytes,
            file_name=file.filename or "handbook.pdf",
            version_label=version_label,
            admin_user=admin,
            db=db,
        )
        return version
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get(
    "/versions/{version_id}",
    response_model=AphVersionResponse,
    summary="Get APH version detail",
)
def get_version(
    version_id: uuid.UUID,
    _admin: User = Depends(require_roles(["main_admin"])),
    db: Session = Depends(get_db),
) -> AphVersionResponse:
    version = db.get(AphVersion, version_id)
    if not version:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="APH version not found.")
    return version


@router.get(
    "/versions/{version_id}/pdf-url",
    summary="Generate signed URL to access the uploaded PDF",
)
def get_pdf_signed_url(
    version_id: uuid.UUID,
    _admin: User = Depends(require_roles(["main_admin"])),
    db: Session = Depends(get_db),
) -> dict:
    version = db.get(AphVersion, version_id)
    if not version or not version.file_key:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="APH file not found.")

    url = storage_service.generate_signed_url(version.file_key, expires_in=3600)
    return {"signed_url": url, "expires_in": 3600}


# ---------------------------------------------------------------------------
# Extraction Endpoint (main_admin)
# ---------------------------------------------------------------------------

@router.post(
    "/versions/{version_id}/extract",
    summary="Trigger background rule extraction via Gemini",
)
def trigger_extraction(
    version_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    page_start: int = Query(default=1, ge=1),
    page_end: int = Query(default=15, ge=1),
    force: bool = Query(default=False),
    admin: User = Depends(require_roles(["main_admin"])),
    db: Session = Depends(get_db),
) -> dict:
    version = db.get(AphVersion, version_id)
    if not version:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="APH version not found.")

    if version.status == "published":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot re-extract rules for a published version.",
        )

    # Reject if already running and recent (<10 min)
    if version.extraction_status == "running":
        age_seconds = (datetime.now(timezone.utc) - version.updated_at).total_seconds()
        if age_seconds < 600:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Extraction is already running for this version.",
            )

    version.extraction_status = "running"
    db.commit()

    record_audit(
        action="start_extraction",
        user_id=admin.id,
        entity_type="aph_version",
        entity_id=version_id,
        detail=f"Pages {page_start}-{page_end}, force={force}",
    )

    background_tasks.add_task(
        aph_service.run_extraction_job,
        version_id=version_id,
        page_start=page_start,
        page_end=page_end,
        force=force,
        admin_user_id=admin.id,
    )

    return {"status": "running", "version_id": str(version_id)}


# ---------------------------------------------------------------------------
# Rule CRUD Endpoints (main_admin)
# ---------------------------------------------------------------------------

@router.get(
    "/versions/{version_id}/rules",
    response_model=list[AphRuleResponse],
    summary="Get rules for an APH version",
)
def list_rules(
    version_id: uuid.UUID,
    programme_key: Optional[str] = Query(default=None),
    needs_review: Optional[bool] = Query(default=None),
    _admin: User = Depends(require_roles(["main_admin"])),
    db: Session = Depends(get_db),
) -> list[AphRuleResponse]:
    stmt = select(AphRule).where(AphRule.aph_version_id == version_id)
    if programme_key:
        stmt = stmt.where(AphRule.programme_key == programme_key)
    if needs_review is not None:
        stmt = stmt.where(AphRule.needs_review == needs_review)

    stmt = stmt.order_by(AphRule.category, AphRule.parameter)
    return db.execute(stmt).scalars().all()


@router.post(
    "/versions/{version_id}/rules",
    response_model=AphRuleResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add a manual rule to a draft APH version",
)
def create_rule(
    version_id: uuid.UUID,
    payload: AphRuleCreateRequest,
    admin: User = Depends(require_roles(["main_admin"])),
    db: Session = Depends(get_db),
) -> AphRuleResponse:
    version = db.get(AphVersion, version_id)
    if not version:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="APH version not found.")
    if version.status == "published":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot add rules to a published version.",
        )

    # Check for duplicate
    existing = db.execute(
        select(AphRule).where(
            AphRule.aph_version_id == version_id,
            AphRule.programme_key == payload.programme_key,
            AphRule.parameter_key == payload.parameter_key,
        )
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Rule with key '{payload.parameter_key}' already exists for programme '{payload.programme_key}'.",
        )

    rule = AphRule(
        aph_version_id=version_id,
        programme=payload.programme,
        programme_key=payload.programme_key,
        category=payload.category,
        parameter=payload.parameter,
        parameter_key=payload.parameter_key,
        operator=payload.operator,
        string_value=payload.string_value,
        numeric_value=payload.numeric_value,
        unit=payload.unit,
        source_page=payload.source_page,
        source_quote=payload.source_quote,
        needs_review=False,
        is_ai_suggested=False,
        edited_by=admin.id,
        edited_at=datetime.now(timezone.utc),
    )
    db.add(rule)
    db.commit()
    db.refresh(rule)

    record_audit(
        action="add_rule",
        user_id=admin.id,
        entity_type="aph_rule",
        entity_id=rule.id,
        detail=f"Added rule: {rule.parameter_key}",
    )
    return rule


@router.patch(
    "/rules/{rule_id}",
    response_model=AphRuleResponse,
    summary="Update a rule (draft version only)",
)
def update_rule(
    rule_id: uuid.UUID,
    payload: AphRuleUpdateRequest,
    admin: User = Depends(require_roles(["main_admin"])),
    db: Session = Depends(get_db),
) -> AphRuleResponse:
    rule = db.get(AphRule, rule_id)
    if not rule:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rule not found.")
    if rule.aph_version.status == "published":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot modify rules of a published APH version.",
        )

    update_data = payload.dict(exclude_unset=True)
    for field, val in update_data.items():
        setattr(rule, field, val)

    rule.is_ai_suggested = False
    rule.edited_by = admin.id
    rule.edited_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(rule)

    record_audit(
        action="edit_aph_rule",
        user_id=admin.id,
        entity_type="aph_rule",
        entity_id=rule.id,
        detail=f"Updated rule: {rule.parameter_key}",
    )
    return rule


@router.delete(
    "/rules/{rule_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a rule (draft version only)",
)
def delete_rule(
    rule_id: uuid.UUID,
    admin: User = Depends(require_roles(["main_admin"])),
    db: Session = Depends(get_db),
):
    rule = db.get(AphRule, rule_id)
    if not rule:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rule not found.")
    if rule.aph_version.status == "published":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot delete rules from a published APH version.",
        )

    db.delete(rule)
    db.commit()

    record_audit(
        action="delete_aph_rule",
        user_id=admin.id,
        entity_type="aph_rule",
        entity_id=rule_id,
        detail=f"Deleted rule: {rule.parameter_key}",
    )
    return None


# ---------------------------------------------------------------------------
# Publish Endpoint (main_admin)
# ---------------------------------------------------------------------------

@router.post(
    "/versions/{version_id}/publish",
    response_model=AphVersionResponse,
    summary="Publish an APH version (immutable after publishing)",
)
def publish_version(
    version_id: uuid.UUID,
    payload: AphPublishRequest,
    admin: User = Depends(require_roles(["main_admin"])),
    db: Session = Depends(get_db),
) -> AphVersionResponse:
    version = db.get(AphVersion, version_id)
    if not version:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="APH version not found.")

    if version.status == "published":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Version is already published.",
        )

    if not version.rules:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot publish a version with no rules.",
        )

    # Check for rules requiring review
    unreviewed = [str(r.id) for r in version.rules if r.needs_review]
    if unreviewed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot publish: {len(unreviewed)} rule(s) require review. Flagged rule IDs: {', '.join(unreviewed[:5])}",
        )

    version.status = "published"
    version.published_at = datetime.now(timezone.utc)
    version.published_by = admin.id
    version.effective_date = payload.effective_date

    db.commit()
    db.refresh(version)

    record_audit(
        action="publish_aph_version",
        user_id=admin.id,
        entity_type="aph_version",
        entity_id=version.id,
        detail=f"Published version: {version.version_label} with effective date {payload.effective_date}",
    )
    return version

