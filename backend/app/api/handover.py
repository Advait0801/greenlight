"""Handover packet routes: build the packets (code only) and record a person's approval of an edited packet."""

from __future__ import annotations

import hashlib
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy.orm import Session

from app.api.deps import require_calendar, require_ruleset
from app.api.plans import _as_of
from app.api.usg import ClubAccess, _club_row
from app.config import get_settings
from app.db import get_session
from app.models import AuditLog
from app.rules import AcademicCalendar, RuleSet
from app.schemas.plans import YearPlanRequest
from app.services.handover import HandoverPacket, build_handover

router = APIRouter(prefix="/handover", tags=["handover"])


class SentReference(ClubAccess):
    reference: str = Field(min_length=1, max_length=32)


class HandoverRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    plan: YearPlanRequest
    # Applications the club sent to the USG screen, each with the club's own token. A wrong token is refused (404),
    # so a club cannot read another club's application into its packet.
    applications: list[SentReference] = Field(default_factory=list, max_length=40)


@router.post("")
def handover(body: HandoverRequest, ruleset: RuleSet = Depends(require_ruleset),
             calendar: AcademicCalendar = Depends(require_calendar), session: Session = Depends(get_session)) -> HandoverPacket:
    rows = [_club_row(a.reference.strip(), a.club_token.strip(), session) for a in body.applications]
    unique = list({row.id: row for row in rows}.values())
    return build_handover(body.plan, unique, ruleset, calendar, _as_of(body.plan), get_settings().rules_dir / "sources")


class PacketApproval(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role: str = Field(min_length=1, max_length=60)
    text: str = Field(min_length=1, max_length=50000)

    @field_validator("text")
    @classmethod
    def _not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("the packet is empty")
        return value


@router.post("/approve")
def approve(body: PacketApproval, session: Session = Depends(get_session)) -> dict[str, Any]:
    digest = hashlib.sha256(body.text.encode("utf-8")).hexdigest()
    session.add(AuditLog(club_id=None, actor="user:officer", action="approval", subject_type="handover_packet",
                         subject_id=digest[:16], payload={"sha256": digest, "role": body.role, "characters": len(body.text)}))
    session.commit()
    return {"approved": True, "sha256": digest, "message": "Approved. Copy the packet to the next officer yourself; Greenlight sends nothing."}


__all__ = ["router"]
