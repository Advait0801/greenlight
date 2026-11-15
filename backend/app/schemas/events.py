"""Event packet types: the facts about an event (from the officer or the reading step) and the packet the
rule engine and deadline calculator build from them. Every date here comes from code."""

from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.common import Citation, Finding

VenueType = Literal["venue_tes_meeting_room", "venue_tes_large", "venue_outdoor", "venue_classroom", "venue_off_campus"]
Status = Literal["to_do", "condition", "blocked", "office_decides", "check_with_office"]
InputField = Literal["event_date", "end_date", "venue", "headcount", "attributes"]

STATUS_LABELS: dict[str, str] = {
    "to_do": "To do",
    "condition": "Rule to keep",
    "blocked": "Blocked as described",
    "office_decides": "The office decides",
    "check_with_office": "Check with the office",
}

MAX_HEADCOUNT = 1_000_000
# Dates outside these years cannot be checked (the calendar and rules are for 2026-27) and could not be shifted safely.
EARLIEST = date(2000, 1, 1)
LATEST = date(2100, 12, 31)
MAX_ATTRIBUTES = 80


class EventFacts(BaseModel):
    """What is known about one event. `attributes` are names from rules/vocabulary.json the officer
    confirmed (or the reading step read with high confidence); `possible_attributes` are ones it was unsure
    about. A possible attribute never removes an obligation: the rules it triggers are listed as
    'check with the office'."""

    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, max_length=200)
    event_date: date | None = None
    end_date: date | None = None
    venue: VenueType | None = None
    headcount: int | None = Field(default=None, ge=0, le=MAX_HEADCOUNT)
    attributes: list[str] = Field(default_factory=list, max_length=MAX_ATTRIBUTES)
    possible_attributes: list[str] = Field(default_factory=list, max_length=MAX_ATTRIBUTES)
    # Fields the reading step could not read with confidence; the officer must answer them.
    needs_officer_input: list[InputField] = Field(default_factory=list)

    @model_validator(mode="after")
    def _consistent(self) -> EventFacts:
        for value in (self.event_date, self.end_date):
            if value is not None and not (EARLIEST <= value <= LATEST):
                raise ValueError(f"dates must be between {EARLIEST.year} and {LATEST.year}")
        if self.end_date is not None and self.event_date is None:
            raise ValueError("an end date needs a start date")
        if self.end_date is not None and self.event_date is not None and self.end_date < self.event_date:
            raise ValueError("the event cannot end before it starts")
        if self.event_date is not None and self.end_date is not None and (self.end_date - self.event_date).days > 366:
            raise ValueError("an event can last at most a year")
        return self


class Fallback(BaseModel):
    kind: Literal["move_date", "change_format", "other_funding"]
    text: str
    earliest_date: date | None = None


class PacketObligation(BaseModel):
    """One form, approval, deadline or condition that applies to the event."""

    rule_id: str
    title: str
    owner_office: str
    status: Status
    status_label: str
    due: date | None
    # How the due date was found: "computed" by the deadline calculator, or why there is none.
    due_note: str | None
    violated: bool
    past_due: bool
    message: str
    note: str | None
    fix: str | None
    # A finding is attached for every obligation shown red, yellow, office decides or green; to-do items and
    # rules to keep carry their citation only. Never green on an office-decides or unverified rule.
    finding: Finding | None
    citation: Citation
    link: str
    # The attributes that brought this rule in.
    triggered_by: list[str]
    from_possible_attribute: bool
    fallbacks: list[Fallback] = Field(default_factory=list)
    # Set when sources disagree and Greenlight applies another, stricter rule instead of this one. The item stays
    # listed (with its citation) but is left out of the timeline, the calendar file and the hard blocks.
    superseded_by: str | None = None


class SourceConflict(BaseModel):
    rules: list[str]
    applied: str | None
    explanation: str
    citations: list[Citation]


class TimelineEntry(BaseModel):
    day: date
    rule_id: str
    title: str
    status: Status
    past_due: bool


class EventPacket(BaseModel):
    as_of: date
    event: EventFacts
    obligations: list[PacketObligation]
    timeline: list[TimelineEntry]
    source_conflicts: list[SourceConflict]
    hard_blocks: list[str]
    questions: list[str]
    fallbacks: list[Fallback]
    counts: dict[str, int]
    notice: str
