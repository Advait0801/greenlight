"""The rule object (PROJECT_CONTEXT section 5) as a strict Pydantic model.

Unknown fields are rejected so that a misspelt field name fails loudly instead of being ignored.
Numbers that drive checks live in `params` or in the deadline fields, never in Python code.
"""

from __future__ import annotations

import re
from datetime import date
from typing import Annotated, Any, Literal

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, StrictInt, field_validator, model_validator


def _iso_date_string(value: Any) -> Any:
    """Dates must be written as ISO strings ("2026-10-21"); a number such as a Unix timestamp is refused."""
    if isinstance(value, date):
        return value
    if not isinstance(value, str):
        raise ValueError("must be a date written as YYYY-MM-DD")
    return value


IsoDate = Annotated[date, BeforeValidator(_iso_date_string)]

Domain = Literal["funding", "events", "outside_money", "recognition"]

# read        source_text appears verbatim in the snapshot (checked by code at load time)
# fetched     the source was only seen through a summarising tool; wording not checked
# unverified  not confirmed; an open question for a human
Verified = Literal["read", "fetched", "unverified"]

# There is deliberately no "green": a rule describes what can go wrong. Green is a verdict the
# rule engine gives a specific item after checking it, never a property of a rule.
#   red             breaks the rule (the board may still make an exception; the message says so)
#   yellow          needs a human look
#   office_decides  the owning office uses judgment; shown as "contact them by <date>"
#   info            context the officer should know; never a pass or fail
Severity = Literal["red", "yellow", "office_decides", "info"]

Kind = Literal[
    "deadline",  # something due a fixed time before or after an anchor date
    "cap",  # a numeric limit
    "ineligible",  # an expense USG does not fund
    "requirement",  # a document, form, approval or condition that must be in place
    "blocked_period",  # dates when something cannot happen
    "allowed",  # a way to raise money that USC allows (with conditions)
    "banned",  # a way to raise money that USC does not allow
    "fund",  # one of the four USG funds
    "clause",  # a clause of the constitution template
    "info",  # context only
]

Unit = Literal["hours", "days", "weeks", "months", "business_days", "academic_weeks"]
Anchor = Literal[
    "event_date",  # first day of the event
    "event_end_date",  # last day of the event
    "initial_payment_due_date",  # USG: the first payment to a vendor
    "travel_date",  # USG Professional/Academic Fund: the first day of travel
    "notification_date",  # e.g. notice that an application is incomplete
    "decision_received_date",  # the day the club receives a decision (e.g. on recognition)
]
Direction = Literal["before", "after"]

RULE_ID = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
REQUIRED_FIELDS = ("source_url", "source_text", "effective_date", "verified")
DEADLINE_FIELDS = ("anchor", "offset", "unit", "direction")


class Rule(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)

    id: str = Field(min_length=3, max_length=120)
    domain: Domain
    kind: Kind
    title: str = Field(min_length=3, max_length=200)
    owner_office: str = Field(min_length=2)
    source: str = Field(min_length=3)
    source_section: str | None = None
    source_url: str
    source_text: str = Field(min_length=10)
    effective_date: IsoDate
    verified: Verified
    verification_note: str | None = None
    severity: Severity
    message: str = Field(min_length=5)
    fix_template: str | None
    applies_to: str = Field(min_length=3)
    check: str | None = None
    # Names from rules/vocabulary.json. The rule applies when any trigger is present
    # (trigger_mode "any") or only when all of them are (trigger_mode "all").
    triggers: list[str] = Field(default_factory=list)
    trigger_mode: Literal["any", "all"] = "any"
    # Numbers and settings the checks use. Two naming conventions are checked at load time:
    #   keys ending in "_quote" hold text that must appear in source_text;
    #   keys ending in "_rules" hold lists of rule ids that must exist.
    params: dict[str, Any] = Field(default_factory=dict)
    anchor: Anchor | None = None
    offset: StrictInt | None = Field(default=None, ge=0, le=730)
    unit: Unit | None = None
    direction: Direction | None = None
    conflicts_with: list[str] | None = None
    depends_on: list[str] = Field(default_factory=list)
    notes: str | None = None

    @field_validator("id")
    @classmethod
    def _id_format(cls, value: str) -> str:
        if not RULE_ID.match(value):
            raise ValueError("must be lowercase words joined by hyphens, e.g. 'usg-food-cap'")
        return value

    @field_validator("source_url")
    @classmethod
    def _https(cls, value: str) -> str:
        if not value.startswith("https://") or " " in value:
            raise ValueError("must be an https:// link with no spaces")
        return value

    @field_validator("triggers", "depends_on")
    @classmethod
    def _no_blank_entries(cls, value: list[str]) -> list[str]:
        if any(not isinstance(item, str) or not item.strip() for item in value):
            raise ValueError("entries must be non-empty strings")
        if len(set(value)) != len(value):
            raise ValueError("entries must not repeat")
        return value

    @model_validator(mode="after")
    def _consistent(self) -> Rule:
        deadline_values = [getattr(self, name) for name in DEADLINE_FIELDS]
        if self.kind == "deadline":
            missing = [name for name, value in zip(DEADLINE_FIELDS, deadline_values, strict=True) if value is None]
            if missing:
                raise ValueError(f"a deadline rule needs {', '.join(missing)}")
        elif any(value is not None for value in deadline_values):
            raise ValueError("anchor, offset, unit and direction are only allowed on deadline rules")
        if self.verified != "read" and not self.verification_note:
            raise ValueError(f"a rule marked '{self.verified}' needs a verification_note saying what to confirm")
        if self.conflicts_with is not None:
            if not self.conflicts_with:
                raise ValueError("conflicts_with must be null or a non-empty list")
            if self.id in self.conflicts_with:
                raise ValueError("a rule cannot conflict with itself")
        if self.id in self.depends_on:
            raise ValueError("a rule cannot depend on itself")
        return self


class RuleFile(BaseModel):
    """One rules/<domain>.json file."""

    model_config = ConfigDict(extra="forbid")

    domain: Domain
    description: str
    rules: list[Any]  # each entry is checked one by one, so one bad rule gets its own message
