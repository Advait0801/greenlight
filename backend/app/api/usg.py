"""USG screen routes.

Club side (no reviewer passcode):
  POST /usg/send                         a club sends one checked application, with its explicit consent; it gets a
                                         reference and a secret token (shown once; only its hash is kept)
  POST /usg/sent/{reference}             the club reads its own application's status with its token
  POST /usg/sent/{reference}/withdraw    the club withdraws it; it leaves the queue and the chart

Reviewer side (X-Reviewer-Key header, compared with USG_REVIEWER_KEY; closed when that is unset):
  GET  /usg/queue, GET /usg/applications/{id}, GET /usg/stats
  POST /usg/applications/{id}/denial-draft    drafted from the reasons the reviewer picks
  POST /usg/applications/{id}/denial-approve  a person approves the edited text; only then can the club see it

Nothing is sent anywhere: the club reads an approved reason on its own status page.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
from datetime import UTC, datetime
from typing import Any, Literal

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import require_calendar, require_ruleset
from app.api.money import _check
from app.config import get_settings
from app.db import get_session
from app.models import AuditLog, SentApplication
from app.rules import AcademicCalendar, RuleSet
from app.schemas.money import MoneyCheckRequest
from app.services.denial_draft import draft_denial
from app.services.usg_screen import ApplicationDetail, FailureStats, QueueItem, detail, failure_stats, queue_item, reasons

router = APIRouter(prefix="/usg", tags=["usg"])
MIN_KEY_CHARS = 12


def _digest(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def require_reviewer(x_reviewer_key: str | None = Header(default=None)) -> str:
    configured = get_settings().usg_reviewer_key
    key = configured.get_secret_value() if configured is not None else ""
    if len(key) < MIN_KEY_CHARS:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                            detail={"message": "The USG screen is not set up on this server (USG_REVIEWER_KEY)."})
    if not x_reviewer_key or not hmac.compare_digest(_digest(x_reviewer_key), _digest(key)):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail={"message": "Enter the USG reviewer passcode to open the USG screen."})
    return "usg_reviewer"


class SendRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    club_name: str = Field(min_length=1, max_length=200)
    # The club must say yes in so many words: nothing reaches the USG screen otherwise.
    consent: Literal[True]
    check: MoneyCheckRequest

    @field_validator("club_name")
    @classmethod
    def _not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("enter the club's name")
        return value.strip()


@router.post("/send")
def send(body: SendRequest, ruleset: RuleSet = Depends(require_ruleset), calendar: AcademicCalendar = Depends(require_calendar),
         session: Session = Depends(get_session)) -> dict[str, Any]:
    """The club sends one application. The report is worked out again here from the budget, never taken from the page,
    and uploaded documents are not kept."""
    # Checked with the club's documents (their findings, such as a quote total that does not match, must reach the
    # reviewer), then stored without them (phase 5 iteration 2).
    report = _check(body.check.model_copy(update={"as_of": None}), ruleset, calendar)
    request = body.check.model_copy(update={"documents": [], "as_of": None})
    token = secrets.token_urlsafe(24)
    reference = "G-" + secrets.token_hex(5).upper()
    stored_report = report.model_dump(mode="json")
    stored_report["documents"] = []
    row = SentApplication(reference=reference, club_token_sha256=_digest(token), club_name=body.club_name,
                          event_name=request.event.name or "Unnamed event", event_date=request.event.event_date,
                          request=request.model_dump(mode="json"), report=stored_report)
    session.add(row)
    session.flush()
    session.add(AuditLog(club_id=None, actor="user:officer", action="sent_to_usg_screen", subject_type="usg_application",
                         subject_id=reference, payload={"verdict": report.verdict.value}))
    session.commit()
    return {"reference": reference, "club_token": token, "verdict": report.verdict.value,
            "message": "Sent to the USG screen in Greenlight. Keep the reference and the token: you need both to see the "
                       "status or withdraw it. This is not an EngageSC submission; apply in EngageSC yourself."}


class ClubAccess(BaseModel):
    model_config = ConfigDict(extra="forbid")

    club_token: str = Field(min_length=1, max_length=200)


def _club_row(reference: str, token: str, session: Session) -> SentApplication:
    row = session.scalars(select(SentApplication).where(SentApplication.reference == reference)).first()
    expected = row.club_token_sha256 if row is not None else _digest("no such application")
    if row is None or not hmac.compare_digest(_digest(token), expected):
        # The same answer whether the reference exists or the token is wrong.
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail={"message": "No application with that reference and token."})
    return row


@router.post("/sent/{reference}")
def club_status(reference: str, body: ClubAccess, session: Session = Depends(get_session)) -> dict[str, Any]:
    row = _club_row(reference, body.club_token, session)
    approved = row.denial_status == "approved"
    return {"reference": row.reference, "event_name": row.event_name, "status": row.status,
            "sent_at": row.sent_at.isoformat(), "verdict": row.report.get("verdict"),
            "reviewer_message": row.denial_approved_text if approved else None,
            "note": "A reviewer's message appears here only after a person at USG approved it."}


@router.post("/sent/{reference}/withdraw")
def withdraw(reference: str, body: ClubAccess, session: Session = Depends(get_session)) -> dict[str, Any]:
    row = _club_row(reference, body.club_token, session)
    if row.status != "withdrawn":
        row.status = "withdrawn"
        row.withdrawn_at = datetime.now(UTC)
        session.add(AuditLog(club_id=None, actor="user:officer", action="withdrawn_from_usg_screen",
                             subject_type="usg_application", subject_id=row.reference, payload={}))
        session.commit()
    return {"reference": row.reference, "status": row.status}


def _visible(session: Session) -> list[SentApplication]:
    return list(session.scalars(select(SentApplication).where(SentApplication.status == "sent")
                                .order_by(SentApplication.sent_at, SentApplication.id)))


def _reviewer_row(application_id: int, session: Session) -> SentApplication:
    row = session.get(SentApplication, application_id)
    if row is None or row.status != "sent":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"message": "No such application in the queue."})
    return row


@router.get("/queue")
def queue(_: str = Depends(require_reviewer), session: Session = Depends(get_session)) -> dict[str, Any]:
    items: list[QueueItem] = [queue_item(row) for row in _visible(session)]
    return {"applications": [i.model_dump(mode="json") for i in items],
            "note": "Only applications a club chose to send appear here. Greenlight's findings are a pre-check, not a decision."}


@router.get("/applications/{application_id}")
def application(application_id: int, _: str = Depends(require_reviewer),
                session: Session = Depends(get_session)) -> ApplicationDetail:
    return detail(_reviewer_row(application_id, session))


@router.get("/stats")
def stats(_: str = Depends(require_reviewer), ruleset: RuleSet = Depends(require_ruleset),
          session: Session = Depends(get_session)) -> FailureStats:
    return failure_stats(_visible(session), ruleset)


class DenialDraftRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rule_ids: list[str] = Field(min_length=1, max_length=40)


@router.post("/applications/{application_id}/denial-draft")
def denial_draft(application_id: int, body: DenialDraftRequest, _: str = Depends(require_reviewer),
                 session: Session = Depends(get_session)) -> dict[str, Any]:
    row = _reviewer_row(application_id, session)
    if row.denial_status == "approved":
        # The club already reads the approved text; a new draft would make the recorded reasons disagree with it
        # (phase 5 iteration 3).
        raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                            detail={"message": "A reason for this application is already approved and visible to the club."})
    available = reasons(row.report)
    chosen = [r for r in available if r.rule_id in set(body.rule_ids)]
    unknown = sorted(set(body.rule_ids) - {r.rule_id for r in available})
    if unknown:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                            detail={"message": "A reason must be one of this application's own findings.", "unknown": unknown})
    draft = draft_denial(row.club_name, row.event_name, chosen)
    draft.log(session, row.reference)
    row.denial_rule_ids = sorted({r.rule_id for r in chosen})
    row.denial_draft = draft.text
    row.denial_status = "draft"
    session.commit()
    return {"text": draft.text, "notes": draft.notes, "approved": False,
            "notice": "Edit the reason, then approve it. The club sees nothing until a person approves it."}


class DenialApproval(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str = Field(min_length=1, max_length=20000)
    reviewer_name: str = Field(min_length=1, max_length=200)

    @field_validator("text", "reviewer_name")
    @classmethod
    def _not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("this field is empty")
        return value


@router.post("/applications/{application_id}/denial-approve")
def denial_approve(application_id: int, body: DenialApproval, _: str = Depends(require_reviewer),
                   session: Session = Depends(get_session)) -> dict[str, Any]:
    row = _reviewer_row(application_id, session)
    if row.denial_status == "none" or not row.denial_rule_ids:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                            detail={"message": "Draft a reason from the application's findings first."})
    digest = hashlib.sha256(body.text.encode("utf-8")).hexdigest()
    row.denial_status = "approved"
    row.denial_approved_text = body.text
    row.denial_approved_by = body.reviewer_name.strip()
    row.denial_approved_at = datetime.now(UTC)
    session.add(AuditLog(club_id=None, actor=f"user:usg_reviewer:{row.denial_approved_by}", action="approval",
                         subject_type="usg_denial_reason", subject_id=row.reference,
                         payload={"sha256": digest, "characters": len(body.text), "rule_ids": row.denial_rule_ids}))
    session.commit()
    return {"approved": True, "sha256": digest,
            "message": "Approved. The club can now read this reason on its status page. Greenlight sent no email."}


__all__ = ["router"]
