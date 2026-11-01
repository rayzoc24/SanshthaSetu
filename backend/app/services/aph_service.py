"""
APH Service for SanshthaSetu.
Handles PDF upload, page storage, background rule extraction, caching, and publishing.
"""

from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import AphPage, AphRule, AphVersion, User
from app.schemas.aph import AphRuleCreateRequest, AphRuleDraft, AphRuleUpdateRequest
from app.services.audit_service import record_audit
from app.services.gemini_service import gemini_service
from app.services.pdf_service import pdf_service
from app.services.storage_service import storage_service


class AphService:
    @staticmethod
    def upload_aph(
        file_bytes: bytes,
        file_name: str,
        version_label: str,
        admin_user: User,
        db: Session,
    ) -> AphVersion:
        """
        Validate PDF magic bytes & size, upload to S3/Neon, extract pages to DB, and create draft AphVersion.
        """
        pdf_service.validate_pdf_bytes(file_bytes, max_size_mb=25)

        version_id = uuid.uuid4()
        file_key = f"aph/{version_id}/{file_name}"
        storage_service.upload_file(file_bytes, file_key, content_type="application/pdf")

        # Extract pages with PyMuPDF
        pages_data = pdf_service.extract_pages_from_bytes(file_bytes)

        # Concatenate text to compute initial content_hash
        full_text = "".join(text for _, text in pages_data)
        content_hash = hashlib.sha256(full_text.encode("utf-8")).hexdigest()

        version = AphVersion(
            id=version_id,
            version_label=version_label,
            file_key=file_key,
            file_name=file_name,
            status="draft",
            extraction_status="none",
            content_hash=content_hash,
            created_by=admin_user.id,
        )
        db.add(version)
        db.flush()

        for page_no, text in pages_data:
            page = AphPage(
                version_id=version_id,
                page_no=page_no,
                text=text,
            )
            db.add(page)

        db.commit()
        db.refresh(version)

        record_audit(
            action="upload_aph",
            user_id=admin_user.id,
            entity_type="aph_version",
            entity_id=version.id,
            detail=f"Uploaded APH PDF: {file_name} ({len(pages_data)} pages)",
        )
        return version

    @staticmethod
    def run_extraction_job(
        version_id: uuid.UUID,
        page_start: int,
        page_end: int,
        force: bool,
        admin_user_id: uuid.UUID,
    ) -> None:
        """
        Background task: runs Gemini extraction, verifies quotes, and stores rules.
        """
        with SessionLocal() as db:
            version = db.get(AphVersion, version_id)
            if not version:
                return

            try:
                # Load pages for the given range
                pages = (
                    db.execute(
                        select(AphPage)
                        .where(
                            AphPage.version_id == version_id,
                            AphPage.page_no >= page_start,
                            AphPage.page_no <= page_end,
                        )
                        .order_by(AphPage.page_no)
                    )
                    .scalars()
                    .all()
                )

                if not pages:
                    version.extraction_status = "failed"
                    db.commit()
                    return

                pages_text = [(p.page_no, p.text) for p in pages]
                range_text = "".join(p.text for p in pages)
                range_hash = hashlib.sha256(range_text.encode("utf-8")).hexdigest()

                # Cache check: if not forcing and cached version with matching hash exists
                if not force:
                    cached_version = (
                        db.execute(
                            select(AphVersion).where(
                                AphVersion.content_hash == range_hash,
                                AphVersion.extraction_status == "done",
                                AphVersion.id != version_id,
                            )
                        )
                        .scalars()
                        .first()
                    )
                    if cached_version and cached_version.rules:
                        # Copy cached rules
                        for old_rule in cached_version.rules:
                            new_rule = AphRule(
                                aph_version_id=version_id,
                                programme=old_rule.programme,
                                programme_key=old_rule.programme_key,
                                category=old_rule.category,
                                parameter=old_rule.parameter,
                                parameter_key=old_rule.parameter_key,
                                operator=old_rule.operator,
                                string_value=old_rule.string_value,
                                numeric_value=old_rule.numeric_value,
                                unit=old_rule.unit,
                                source_page=old_rule.source_page,
                                source_quote=old_rule.source_quote,
                                needs_review=old_rule.needs_review,
                                is_ai_suggested=True,
                            )
                            db.add(new_rule)
                        version.extraction_status = "done"
                        db.commit()
                        return

                # If force is true and draft, clear existing rules
                if force and version.status == "draft":
                    db.execute(delete(AphRule).where(AphRule.aph_version_id == version_id))
                    db.flush()
                    record_audit(
                        action="force_reextract",
                        user_id=admin_user_id,
                        entity_type="aph_version",
                        entity_id=version_id,
                        detail=f"Forced re-extraction for pages {page_start}-{page_end}",
                    )

                # Call Gemini / fallback extractor
                draft_rules: list[AphRuleDraft] = gemini_service.extract_aph_rules(pages_text)

                # Page text lookup map
                page_text_map = {p.page_no: p.text for p in pages}

                # Load existing rules for upsert / deduplication
                existing_rules = {
                    (r.programme_key, r.parameter_key): r
                    for r in db.execute(
                        select(AphRule).where(AphRule.aph_version_id == version_id)
                    ).scalars().all()
                }

                seen_keys_in_batch = set()
                applied_count = 0

                for draft in draft_rules:
                    key = (draft.programme_key, draft.parameter_key)
                    if key in seen_keys_in_batch:
                        continue
                    seen_keys_in_batch.add(key)

                    # Quote verification
                    page_content = page_text_map.get(draft.source_page, "")
                    quote_found = bool(draft.source_quote and draft.source_quote.strip() in page_content)

                    if key in existing_rules:
                        # Update existing rule
                        rule = existing_rules[key]
                        rule.programme = draft.programme
                        rule.category = draft.category
                        rule.parameter = draft.parameter
                        rule.operator = draft.operator
                        rule.string_value = draft.string_value
                        rule.numeric_value = draft.numeric_value
                        rule.unit = draft.unit
                        rule.source_page = draft.source_page
                        rule.source_quote = draft.source_quote
                        rule.needs_review = not quote_found
                        rule.is_ai_suggested = True
                    else:
                        rule = AphRule(
                            aph_version_id=version_id,
                            programme=draft.programme,
                            programme_key=draft.programme_key,
                            category=draft.category,
                            parameter=draft.parameter,
                            parameter_key=draft.parameter_key,
                            operator=draft.operator,
                            string_value=draft.string_value,
                            numeric_value=draft.numeric_value,
                            unit=draft.unit,
                            source_page=draft.source_page,
                            source_quote=draft.source_quote,
                            needs_review=not quote_found,
                            is_ai_suggested=True,
                        )
                        db.add(rule)
                        existing_rules[key] = rule

                    applied_count += 1

                version.extraction_status = "done"
                version.notes = gemini_service.last_method_note
                version.extraction_log = {
                    "rule_count": applied_count,
                    "method": gemini_service.last_method_note,
                    "page_range": f"{page_start}-{page_end}",
                    "extracted_at": datetime.now(timezone.utc).isoformat(),
                }
                db.commit()

            except Exception as e:
                import logging
                logging.getLogger(__name__).exception("Extraction job failed for version %s: %s", version_id, e)
                db.rollback()
                failed_version = db.get(AphVersion, version_id)
                if failed_version:
                    failed_version.extraction_status = "failed"
                    failed_version.notes = f"Extraction failed: {str(e)}"
                    failed_version.extraction_log = {
                        "error": str(e),
                        "failed_at": datetime.now(timezone.utc).isoformat(),
                    }
                    db.commit()


aph_service = AphService()

