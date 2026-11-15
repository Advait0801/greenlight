from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.ai.client import AIResult
from app.models import AuditLog


def log_ai_output(
    session: Session,
    result: AIResult[Any],
    *,
    club_id: int | None,
    subject_type: str | None = None,
    subject_id: str | None = None,
) -> AuditLog:
    """Record one AI output in the audit log (PROJECT_CONTEXT section 5). The caller commits."""
    entry = AuditLog(
        club_id=club_id,
        actor=f"ai:{result.model}",
        action="ai_output",
        subject_type=subject_type,
        subject_id=subject_id,
        payload=result.audit_payload(),
    )
    session.add(entry)
    return entry
