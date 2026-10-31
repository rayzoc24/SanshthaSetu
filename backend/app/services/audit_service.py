"""
Audit log service.

record_audit() opens its OWN SessionLocal(), commits, and closes.
It does NOT accept the caller's session.

This guarantees the audit row persists even when the caller's
request transaction rolls back (e.g. on a 401 or 403 response).

Never raises — all exceptions are printed to stderr so a failing
audit write never disrupts the request.
"""

from __future__ import annotations

import sys
import uuid
from typing import Optional


def record_audit(
    action: str,
    user_id: Optional[uuid.UUID] = None,
    entity_type: Optional[str] = None,
    entity_id: Optional[uuid.UUID] = None,
    detail: Optional[str] = None,
    ip_address: Optional[str] = None,
) -> None:
    """
    Insert one row into audit_log using an independent session.

    Parameters
    ──────────
    action      Short verb string, e.g. "login", "login_failed", "create".
    user_id     UUID of the acting user; None for unauthenticated events
                (e.g. failed login before the user record is resolved).
    entity_type Table / resource name, e.g. "application".
    entity_id   PK of the affected row.
    detail      Free-form context — for failed logins, store the attempted email.
    ip_address  Client IP, up to 45 chars (covers IPv6).
    """
    # Late imports keep this module importable before the app is fully wired.
    try:
        from app.database import SessionLocal
        from app.models import AuditLog

        entry = AuditLog(
            user_id=user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            detail=detail,
            ip_address=ip_address,
        )

        with SessionLocal() as db:
            db.add(entry)
            db.commit()

    except Exception as exc:  # noqa: BLE001
        # Audit failures must never surface to the caller.
        print(f"[audit] WARNING: failed to write audit row: {exc}", file=sys.stderr)
