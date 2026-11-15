"""Money check routes: read uploaded quotes (AI), read which fund fits (AI), check a budget (code only), draft the
application (AI, only with no red item) and record the officer's approval of the draft.

Nothing here submits anything. The officer pastes the approved draft into EngageSC.
"""

from __future__ import annotations

import hashlib
import io
from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy.orm import Session

from app.api.deps import require_calendar, require_ruleset
from app.api.events import today_at_usc
from app.config import get_settings
from app.db import get_session
from app.models import AuditLog
from app.rules import AcademicCalendar, RuleSet
from app.schemas.money import ATTACHMENT_LABELS, FUND_IDS, MoneyCheckRequest, MoneyReport
from app.services.application_draft import MAX_PURPOSE_CHARS, DraftRefused, draft_application
from app.services.fund_reading import FundReadingError, read_fund
from app.services.money_check import UnknownName, check_budget
from app.services.quote_intake import MAX_TEXT_CHARS, IntakeError, read_quote
from app.services.vendor_list import listed_vendors

router = APIRouter(prefix="/money", tags=["money"])
MAX_FILES = 10
MAX_FILE_BYTES = 20 * 1024 * 1024


def _unprocessable(message: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail={"message": message})


def _sniff(data: bytes) -> str | None:
    """The file's type from its first bytes, never from its name or the browser's label."""
    if data.startswith(b"%PDF-"):
        return "application/pdf"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if data.startswith((b"GIF87a", b"GIF89a")):
        return "image/gif"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    if data.startswith(b"PK\x03\x04"):
        return "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    return None


def _docx_text(data: bytes) -> str:
    import docx

    try:
        document = docx.Document(io.BytesIO(data))
    except Exception as exc:  # python-docx raises several types for a damaged file
        raise IntakeError("The Word file could not be opened.") from exc
    parts = [p.text for p in document.paragraphs]
    for table in document.tables:
        for row in table.rows:
            parts.append(" | ".join(cell.text for cell in row.cells))
    return "\n".join(parts)


def _suggested_lines(documents: list[Any]) -> list[dict[str, Any]]:
    """Budget lines pre-filled from what was read, for the officer to check. Unsure values are left empty."""
    out: list[dict[str, Any]] = []
    for doc in documents:
        channel = {"online_cart": "online_cart", "amazon": "amazon"}.get(doc.kind, "vendor_quote")
        for read in doc.lines:
            out.append({
                "vendor": doc.vendor or "", "item": read.item, "category": read.category, "category_sure": read.category_sure,
                "quantity": read.quantity, "unit_price_cents": read.unit_price_cents, "amount_cents": read.amount_cents,
                "nights": read.nights, "has_quote": doc.readable, "purchase_channel": channel,
                "has_cart_screenshot": True if channel == "online_cart" else None, "has_wish_list_link": None,
                "document": doc.index, "unsure": read.unsure,
            })
    return out


@router.get("/vocabulary")
def vocabulary(ruleset: RuleSet = Depends(require_ruleset)) -> dict[str, Any]:
    """Categories, attachments and funds the page offers, with plain descriptions from the rule table."""
    return {
        "categories": [{"name": n, "description": d} for n, d in ruleset.vocabulary.get("line_item_categories", {}).items()],
        "attachments": [{"name": n, "description": d} for n, d in ATTACHMENT_LABELS.items()],
        "funds": [{"id": f, "name": ruleset.get(f).params.get("fund", ruleset.get(f).title), "description": ruleset.get(f).message}
                  for f in FUND_IDS if f in ruleset],
        "event_details": [{"name": n, "description": ruleset.vocabulary["event_attributes"][n]}
                          for n in ("private_residence", "international_travel") if n in ruleset.vocabulary.get("event_attributes", {})]
                         + [{"name": "other_usc_funding", "description": ruleset.vocabulary.get("facts", {}).get("other_usc_funding", "")}],
    }


@router.post("/read")
async def read_documents(files: list[UploadFile] = File(default=[]), text: str = Form(default=""),
                         ruleset: RuleSet = Depends(require_ruleset), session: Session = Depends(get_session)) -> dict[str, Any]:
    """Read uploaded quotes, cart screenshots or invoices (and pasted text). Each document is read on its own; one
    that cannot be read is reported, never passed."""
    if len(files) > MAX_FILES:
        raise _unprocessable(f"Upload at most {MAX_FILES} files at a time.")
    if not files and not text.strip():
        raise _unprocessable("Upload a quote or paste its text.")
    if len(text) > MAX_TEXT_CHARS:
        raise _unprocessable(f"The pasted text is longer than {MAX_TEXT_CHARS:,} characters.")
    documents = []
    problems: list[dict[str, str]] = []
    index = 0
    sources: list[tuple[str, bytes | None, str | None]] = []
    if text.strip():
        sources.append(("pasted text", None, text))
    for upload in files:
        data = await upload.read(MAX_FILE_BYTES + 1)
        name = (upload.filename or "upload")[:200]
        if len(data) > MAX_FILE_BYTES:
            problems.append({"name": name, "message": "The file is larger than 20 MB."})
            continue
        sources.append((name, data, None))
    for name, data, pasted in sources:
        index += 1
        try:
            if pasted is not None:
                read = read_quote(index=index, name=name, text=pasted, ruleset=ruleset)
            else:
                assert data is not None
                kind = _sniff(data)
                if kind is None:
                    try:
                        decoded = data.decode("utf-8")
                    except UnicodeDecodeError:
                        raise IntakeError("Greenlight can read PDF, PNG, JPEG, GIF, WebP, Word (.docx) and text files only.") from None
                    read = read_quote(index=index, name=name, text=decoded, ruleset=ruleset)
                elif kind.endswith("document"):
                    read = read_quote(index=index, name=name, text=_docx_text(data), ruleset=ruleset)
                else:
                    read = read_quote(index=index, name=name, data=data, media_type=kind, ruleset=ruleset)
        except IntakeError as exc:
            problems.append({"name": name, "message": str(exc)})
            continue
        read.log(session)
        documents.append(read.document)
    session.commit()
    return {
        "documents": [doc.model_dump(mode="json") for doc in documents],
        "suggested_lines": _suggested_lines(documents),
        "problems": problems,
    }


class FundRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(default="", max_length=200)
    description: str = Field(default="", max_length=2000)


@router.post("/fund")
def fund(body: FundRequest, ruleset: RuleSet = Depends(require_ruleset), session: Session = Depends(get_session)) -> dict[str, Any]:
    try:
        read = read_fund(body.name, body.description, ruleset=ruleset)
    except FundReadingError as exc:
        raise _unprocessable(str(exc)) from exc
    read.log(session)
    session.commit()
    return {"reading": read.reading.model_dump(mode="json")}


def _as_of(value: date | None) -> date:
    today = today_at_usc()
    if value is not None and abs((value - today).days) > 3 * 366:
        raise _unprocessable("as_of must be within three years of today")
    return value or today


def _check(body: MoneyCheckRequest, ruleset: RuleSet, calendar: AcademicCalendar) -> MoneyReport:
    vendors = listed_vendors(ruleset, get_settings().rules_dir / "sources")
    try:
        return check_budget(body, ruleset, calendar, _as_of(body.as_of), vendors)
    except UnknownName as exc:
        raise _unprocessable(str(exc)) from exc


@router.post("/check")
def check(body: MoneyCheckRequest, ruleset: RuleSet = Depends(require_ruleset),
          calendar: AcademicCalendar = Depends(require_calendar)) -> MoneyReport:
    """Code only: the budget against the rule table. Every figure and verdict is computed here."""
    return _check(body, ruleset, calendar)


class DraftRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    check: MoneyCheckRequest
    purpose: str = Field(default="", max_length=MAX_PURPOSE_CHARS)


@router.post("/draft")
def draft(body: DraftRequest, ruleset: RuleSet = Depends(require_ruleset), calendar: AcademicCalendar = Depends(require_calendar),
          session: Session = Depends(get_session)) -> dict[str, Any]:
    """Draft the application text. The report is worked out again here, so no draft is written while a red item
    remains, whatever the page sends."""
    # Always as of today: a back-dated as_of must never unblock a draft (phase 3 iteration 2).
    check_today = body.check.model_copy(update={"as_of": None})
    report = _check(check_today, ruleset, calendar)
    try:
        result = draft_application(check_today, report, body.purpose)
    except DraftRefused as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                            detail={"message": str(exc), "blocked_by": exc.blocked_by}) from exc
    result.log(session)
    session.commit()
    return {"text": result.text, "sections": result.sections, "notes": result.notes, "approved": False,
            "notice": "Edit the draft, then approve it. Greenlight does not submit anything."}


class ApprovalRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str = Field(min_length=1, max_length=20000)
    event_name: str = Field(default="", max_length=200)

    @field_validator("text")
    @classmethod
    def _not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("the draft is empty")
        return value


@router.post("/draft/approve")
def approve(body: ApprovalRequest, session: Session = Depends(get_session)) -> dict[str, Any]:
    """Record that a person approved this text. Only a fingerprint is kept; nothing is sent anywhere."""
    digest = hashlib.sha256(body.text.encode("utf-8")).hexdigest()
    session.add(AuditLog(club_id=None, actor="user:officer", action="approval", subject_type="application_draft",
                         subject_id=digest[:16], payload={"sha256": digest, "characters": len(body.text)}))
    session.commit()
    return {"approved": True, "sha256": digest,
            "message": "Approved. Copy the text into EngageSC yourself; Greenlight has not submitted anything."}


__all__ = ["router"]
