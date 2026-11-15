"""Event packet routes: read a sentence into event facts (AI), and build the packet from facts (code only).

Nothing here submits anything. The packet is a pre-check; the officer checks every item with its office.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy.orm import Session

from app.api.deps import require_calendar, require_ruleset
from app.db import get_session
from app.rules import AcademicCalendar, RuleSet
from app.schemas.events import EventFacts, EventPacket
from app.services.event_intake import MAX_SENTENCE_CHARS, IntakeError, parse_sentence
from app.services.ics import packet_to_ics
from app.services.rule_engine import UnknownAttribute, build_packet

router = APIRouter(prefix="/events", tags=["events"])
USC_TIME = ZoneInfo("America/Los_Angeles")


def today_at_usc() -> date:
    return datetime.now(USC_TIME).date()


class ParseRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sentence: str = Field(min_length=1, max_length=MAX_SENTENCE_CHARS)


class PacketRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event: EventFacts
    # The day the packet is worked out for (default: today in Los Angeles). Only for previews and tests.
    as_of: date | None = None

    @field_validator("as_of")
    @classmethod
    def _near_today(cls, value: date | None) -> date | None:
        if value is not None and abs((value - today_at_usc()).days) > 3 * 366:
            raise ValueError("as_of must be within three years of today")
        return value


@router.post("/parse")
def parse(body: ParseRequest, ruleset: RuleSet = Depends(require_ruleset),
          session: Session = Depends(get_session)) -> dict[str, Any]:
    """Read the officer's sentence. Unsure values come back as questions, never as guesses."""
    try:
        parsed = parse_sentence(body.sentence, ruleset=ruleset)
    except IntakeError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail={"message": str(exc)}) from exc
    parsed.log(session)
    session.commit()
    return {
        "facts": parsed.facts.model_dump(mode="json"),
        "readings": parsed.readings,
        "notes": parsed.notes,
        "sentence_had_instructions": parsed.sentence_had_instructions,
    }


def _packet(body: PacketRequest, ruleset: RuleSet, calendar: AcademicCalendar) -> EventPacket:
    try:
        return build_packet(body.event, ruleset, calendar, body.as_of or today_at_usc())
    except UnknownAttribute as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail={"message": str(exc)}) from exc


@router.post("/packet")
def packet(body: PacketRequest, ruleset: RuleSet = Depends(require_ruleset),
           calendar: AcademicCalendar = Depends(require_calendar)) -> EventPacket:
    return _packet(body, ruleset, calendar)


@router.post("/packet.ics")
def packet_ics(body: PacketRequest, ruleset: RuleSet = Depends(require_ruleset),
               calendar: AcademicCalendar = Depends(require_calendar)) -> Response:
    text = packet_to_ics(_packet(body, ruleset, calendar))
    return Response(content=text, media_type="text/calendar; charset=utf-8",
                    headers={"Content-Disposition": 'attachment; filename="greenlight-event.ics"'})


__all__ = ["router"]
