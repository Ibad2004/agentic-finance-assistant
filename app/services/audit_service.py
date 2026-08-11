"""Append-only application service for recording audit events."""

from collections.abc import Mapping
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.db.models import AuditLog


def record_audit_log(
    session: Session,
    *,
    user_id: UUID,
    action_type: str,
    entity_type: str,
    entity_id: UUID | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> AuditLog:
    """Append an audit log entry; updates and deletes are intentionally not provided here."""

    audit_log = AuditLog(
        user_id=user_id,
        action_type=action_type,
        entity_type=entity_type,
        entity_id=entity_id,
        metadata_=dict(metadata) if metadata is not None else None,
    )
    session.add(audit_log)
    return audit_log
