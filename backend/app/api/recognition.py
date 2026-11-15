"""Recognition check routes: the constitution check and the readiness tracker.

Nothing here submits anything. Both routes return a pre-check for the officer to act on.
"""

from __future__ import annotations

import logging
from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import require_ruleset
from app.db import get_session
from app.models import AuditLog
from app.rules import RuleSet
from app.services.recognition import check_upload
from app.services.recognition_check import CLUB_FLAGS, ConstitutionReport
from app.services.recognition_document import MAX_TEXT_CHARS, MAX_UPLOAD_BYTES
from app.services.recognition_readiness import ReadinessInput, ReadinessReport, readiness

router = APIRouter(tags=["recognition"])
log = logging.getLogger(__name__)

_YES_NO = {"yes": True, "true": True, "no": False, "false": False}


def _flag(name: str, value: str | None) -> bool | None:
    """yes / no; anything left out means "not sure", which the check treats as yes (the clause is required)."""
    if value is None or not value.strip() or value.strip().lower() in ("unknown", "unsure", "not_sure"):
        return None
    try:
        return _YES_NO[value.strip().lower()]
    except KeyError:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                            detail=f"{name} must be yes, no or left out.") from None


def _audit(session: Session, results: list[Any]) -> None:
    """Every AI output goes in the audit log. A failure to log never fails the check."""
    try:
        for result in results:
            session.add(AuditLog(club_id=None, actor=f"ai:{result.model}", action="ai_output",
                                 subject_type="constitution", subject_id=result.request_key[:16],
                                 payload=result.audit_payload()))
        session.commit()
    except Exception:  # the audit table is a record, not a gate
        session.rollback()
        log.exception("could not write the audit log")


@router.post("/constitution/check", response_model=ConstitutionReport)
async def constitution_check(
    file: UploadFile | None = File(default=None, description="The constitution as PDF, DOCX or text"),
    text: str | None = Form(default=None, description="The constitution's text, pasted"),
    has_parent_organization: str | None = Form(default=None),
    has_school_affiliation: str | None = Form(default=None),
    has_additional_officers: str | None = Form(default=None),
    has_appointed_positions: str | None = Form(default=None),
    ruleset: RuleSet = Depends(require_ruleset),
    session: Session = Depends(get_session),
) -> ConstitutionReport:
    """Compare a constitution with the template, clause by clause. Send a file or pasted text, not both."""
    given = dict(zip(CLUB_FLAGS, (has_parent_organization, has_school_affiliation, has_additional_officers,
                                  has_appointed_positions), strict=True))
    club = {name: _flag(name, value) for name, value in given.items()}
    has_file = file is not None and bool(file.filename or file.size)
    has_text = text is not None and bool(text.strip())
    if has_file and has_text:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                            detail="Send either a file or pasted text, not both.")
    if has_file and file is not None:
        data = await file.read(MAX_UPLOAD_BYTES + 1)
        report, results = check_upload(ruleset, club, filename=file.filename or "upload", data=data)
    else:
        if text is not None and len(text) > MAX_TEXT_CHARS:
            raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                                detail=f"The pasted text is longer than {MAX_TEXT_CHARS:,} characters.")
        report, results = check_upload(ruleset, club, text=text or "")
    _audit(session, results)
    return report


@router.get("/recognition/readiness", response_model=ReadinessReport)
def readiness_blank(
    as_of: date | None = Query(default=None, description="Count days from this date instead of today"),
    ruleset: RuleSet = Depends(require_ruleset),
) -> ReadinessReport:
    """The checklist with nothing ticked: every item, its rule and the key dates."""
    return readiness(ruleset, ReadinessInput(), as_of)


@router.post("/recognition/readiness", response_model=ReadinessReport)
def readiness_check(
    given: ReadinessInput,
    as_of: date | None = Query(default=None, description="Count days from this date instead of today"),
    ruleset: RuleSet = Depends(require_ruleset),
) -> ReadinessReport:
    """What is done and what is left, from the boxes the officer ticked. Nothing is stored."""
    return readiness(ruleset, given, as_of)
