"""Year plan types: what the officer enters once (club, money, events) and the plan Greenlight builds from it.

Amounts are whole cents. Every date, sum and verdict in a plan comes from code: the event packet's engine
(app.services.rule_engine), the money check's fund matching (app.services.money_check) and the year planner.
The model never produces a figure here; it may only turn a pasted list of events into rows the officer confirms.
"""

from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.common import Citation, Finding, Verdict
from app.schemas.events import EARLIEST, LATEST, MAX_ATTRIBUTES, MAX_HEADCOUNT, EventPacket, Status, VenueType
from app.schemas.money import MAX_CENTS, FundId, FundResult

MAX_EVENTS = 60
MAX_UNAVAILABLE = 366


class PlanEvent(BaseModel):
    """One event the officer plans. The officer supplies it; Greenlight never invents events."""

    model_config = ConfigDict(extra="forbid")

    key: str = Field(min_length=1, max_length=60, pattern=r"^[a-z0-9-]+$")
    name: str = Field(min_length=1, max_length=200)
    event_date: date | None = None
    end_date: date | None = None
    venue: VenueType | None = None
    headcount: int | None = Field(default=None, ge=0, le=MAX_HEADCOUNT)
    attributes: list[str] = Field(default_factory=list, max_length=MAX_ATTRIBUTES)
    possible_attributes: list[str] = Field(default_factory=list, max_length=MAX_ATTRIBUTES)
    estimated_cost_cents: int = Field(default=0, ge=0, le=MAX_CENTS)
    # What the officer would like USG to pay. 0 means the event does not ask USG for money.
    usg_request_cents: int = Field(default=0, ge=0, le=MAX_CENTS)
    # The fund the officer chose, if any. Otherwise the plan shows the fund as unsure.
    fund: FundId | None = None

    @model_validator(mode="after")
    def _consistent(self) -> PlanEvent:
        for value in (self.event_date, self.end_date):
            if value is not None and not (EARLIEST <= value <= LATEST):
                raise ValueError(f"dates must be between {EARLIEST.year} and {LATEST.year}")
        if self.end_date is not None and self.event_date is None:
            raise ValueError("an end date needs a start date")
        if self.end_date is not None and self.event_date is not None:
            if self.end_date < self.event_date:
                raise ValueError("the event cannot end before it starts")
            if (self.end_date - self.event_date).days > 366:
                raise ValueError("an event can last at most a year")
        if self.usg_request_cents > self.estimated_cost_cents:
            raise ValueError("the USG request cannot be more than the event's estimated cost")
        return self


class YearPlanRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    club_name: str = Field(default="", max_length=200)
    mission: str = Field(default="", max_length=2000)
    level: Literal["undergraduate", "graduate"] | None = None
    money_on_hand_cents: int = Field(default=0, ge=0, le=MAX_CENTS)
    expected_income_cents: int = Field(default=0, ge=0, le=MAX_CENTS)
    # Money already received from USG this academic year. None means not known: the yearly cap is then asked about,
    # never assumed to be untouched.
    usg_received_this_year_cents: int | None = Field(default=None, ge=0, le=MAX_CENTS)
    unavailable_dates: list[date] = Field(default_factory=list, max_length=MAX_UNAVAILABLE)
    events: list[PlanEvent] = Field(default_factory=list, max_length=MAX_EVENTS)
    # The day the plan is worked out for (default: today in Los Angeles). Only for previews and tests.
    as_of: date | None = None

    @model_validator(mode="after")
    def _unique(self) -> YearPlanRequest:
        keys = [event.key for event in self.events]
        if len(set(keys)) != len(keys):
            raise ValueError("every event needs its own key")
        for day in self.unavailable_dates:
            if not (EARLIEST <= day <= LATEST):
                raise ValueError(f"dates must be between {EARLIEST.year} and {LATEST.year}")
        return self


ProblemType = Literal[
    "funded_events_over_semester_cap",
    "over_yearly_cap",
    "yearly_cap_unknown",
    "same_day_funding_requests",
    "deadline_in_previous_semester_or_break",
    "usg_deadline_passed_per_table",
    "usg_no_deadline_in_table",
    "not_fundable_as_described",
    "event_in_blocked_period",
    "banned_money_source",
    "banned_at_event",
    "blocked_as_described",
    "deadline_passed",
    "event_date_passed",
    "event_needs_date",
    "outside_calendar",
    "officers_unavailable",
]


class PlanProblem(BaseModel):
    """A problem found early, across one or more events. Every problem that rests on a rule carries the rule's
    citation (and, where the rule allows a verdict, a finding built from the rule table). Problems about the plan's
    own input (a date the officers marked unavailable, an event with no date) have no rule."""

    type: ProblemType
    rule_id: str | None
    severity: Verdict
    severity_label: str
    events: list[str]
    note: str
    fix: str | None
    citation: Citation | None
    finding: Finding | None
    # Further sources behind the note (for example the deadline table's own rule).
    also_cites: list[Citation] = Field(default_factory=list)


class TableDeadline(BaseModel):
    """A USG application deadline for one event: the latest date it can fall on (code, from calendar weeks) and
    what Greenlight's unconfirmed copy of USG's table says."""

    rule_id: str
    title: str
    column: Literal["6_week", "9_week"]
    weeks: int
    # The event date minus `weeks` calendar weeks (counted from the event; the first payment is assumed to be due on or
    # before the event). Not a bound: USG's own table sometimes gives a later date, sometimes an earlier one.
    calendar_count: date
    calendar_count_in: str
    # The earlier of `calendar_count` and `table_date`: the stricter date, the one the plan tells the officer to use.
    apply_by: date
    table_status: Literal["date", "no_deadline", "not_applicable", "not_in_table"]
    table_date: date | None
    table_row_to_confirm: bool
    before_semester: bool
    passed_per_table: bool
    citation: Citation
    table_citation: Citation


class EventBudget(BaseModel):
    key: str
    name: str
    cost_cents: int
    usg_requested_cents: int
    # What the funding strategy plans to ask USG for (never more than requested; 0 when not planned).
    usg_planned_cents: int
    club_money_cents: int
    shortfall_cents: int


class BudgetSummary(BaseModel):
    total_cost_cents: int
    funds_available_cents: int
    gap_before_usg_cents: int
    usg_requested_cents: int
    # Requests plus money already received, over the yearly cap, added up academic year by academic year (None when
    # the amount received this year is unknown and the plan asks USG for money this year).
    usg_requested_over_yearly_cap_cents: int | None
    yearly_cap_cents: int
    usg_planned_cents: int
    club_money_cents: int
    shortfall_cents: int
    unallocated_cents: int
    rows: list[EventBudget]
    explanation: list[str]
    citation: Citation


class FundingStep(BaseModel):
    order: int
    key: str
    name: str
    term: str | None
    requested_cents: int
    planned_cents: int
    status: Literal["apply", "apply_partly"]
    fund: FundResult
    apply_by: TableDeadline | None
    note: str


class NotPlanned(BaseModel):
    key: str
    name: str
    requested_cents: int
    reason: str
    severity: Verdict
    citation: Citation | None


class FundingStrategy(BaseModel):
    steps: list[FundingStep]
    not_planned: list[NotPlanned]
    semester_cap: int
    yearly_cap_cents: int
    explanation: list[str]
    citations: list[Citation]


CalendarKind = Literal["event", "due", "contact_by", "usg_table"]


class CalendarItem(BaseModel):
    day: date
    kind: CalendarKind
    event_key: str
    event_name: str
    rule_id: str | None
    title: str
    status: Status | None
    status_label: str
    past_due: bool
    # True for dates read from the unconfirmed copy of USG's deadline table: always "check with USG".
    unconfirmed: bool
    citation: Citation | None


class CrowdedWeek(BaseModel):
    week_start: date
    week_end: date
    count: int
    events: list[str]


class PlanEventResult(BaseModel):
    key: str
    name: str
    event_date: date | None
    end_date: date | None
    term: str | None
    asks_usg: bool
    verdict: Verdict
    verdict_label: str
    packet: EventPacket
    usg_deadlines: list[TableDeadline]
    budget: EventBudget


class YearPlanReport(BaseModel):
    as_of: date
    club_name: str
    events: list[PlanEventResult]
    calendar: list[CalendarItem]
    crowded_weeks: list[CrowdedWeek]
    budget: BudgetSummary
    strategy: FundingStrategy
    problems: list[PlanProblem]
    this_week: list[CalendarItem]
    questions: list[str]
    counts: dict[str, int]
    notice: str
