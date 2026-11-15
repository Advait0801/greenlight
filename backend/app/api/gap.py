"""Funding gap helper routes: the allowed and banned options (code only), an outreach email draft (AI writes one
paragraph; code writes the rest and filters it) and the officer's approval of the edited email. Nothing is sent."""

from __future__ import annotations

import hashlib
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy.orm import Session

from app.api.deps import require_calendar, require_ruleset
from app.api.money import _as_of
from app.db import get_session
from app.models import AuditLog
from app.rules import AcademicCalendar, RuleSet
from app.services.gap_email import EmailRequest, draft_email
from app.services.gap_helper import GapReport, GapRequest, funding_gap
from app.services.rule_engine import UnknownAttribute

router = APIRouter(prefix="/gap", tags=["gap"])


@router.post("/options")
def options(body: GapRequest, ruleset: RuleSet = Depends(require_ruleset),
            calendar: AcademicCalendar = Depends(require_calendar)) -> GapReport:
    """Code only: the options USC allows, with their rules and lead times, and the ones it does not."""
    try:
        return funding_gap(body, ruleset, calendar, _as_of(body.as_of))
    except UnknownAttribute as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail={"message": str(exc)}) from exc


@router.post("/email")
def email(body: EmailRequest, ruleset: RuleSet = Depends(require_ruleset),
          session: Session = Depends(get_session)) -> dict[str, Any]:
    result = draft_email(body, ruleset)
    result.log(session)
    session.commit()
    return {"subject": result.subject, "text": result.text, "notes": result.notes, "approved": False,
            "notice": "Edit the email, then approve it. Greenlight does not send anything: copy it into your own email."}


class EmailApproval(BaseModel):
    model_config = ConfigDict(extra="forbid")

    subject: str = Field(default="", max_length=300)
    text: str = Field(min_length=1, max_length=20000)

    @field_validator("text")
    @classmethod
    def _not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("the email is empty")
        return value


@router.post("/email/approve")
def approve(body: EmailApproval, session: Session = Depends(get_session)) -> dict[str, Any]:
    """Record that a person approved this text. Only a fingerprint is kept; nothing is sent."""
    digest = hashlib.sha256(f"{body.subject}\n{body.text}".encode()).hexdigest()
    session.add(AuditLog(club_id=None, actor="user:officer", action="approval", subject_type="outreach_email",
                         subject_id=digest[:16], payload={"sha256": digest, "characters": len(body.text)}))
    session.commit()
    return {"approved": True, "sha256": digest,
            "message": "Approved. Copy the email into your own email account; Greenlight has not sent anything."}


__all__ = ["router"]
