"""Funding gap helper (PROJECT_CONTEXT 4E): when an event costs more than the club and USG can cover, list only the
ways of raising money USC allows, each with its rule and lead time, explain the ways it does not allow, and draft an
outreach email for a person to edit and approve.

Code decides everything here. The list of options is fixed by the rule table (rules/outside_money.json), never by the
model, so no prompt can add a cash sponsor, a paid raffle, a brand ambassador or a sponsorship activation to it. Lead
times come from the event packet engine (Phase 2): the option's activity is added to the event and the obligations it
brings are listed with their dates. The outreach email is drafted in app/services/gap_email.py; this module is code only.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator
from app.rules import AcademicCalendar, RuleSet, citation_for, finding_for
from app.schemas.common import PRECHECK_NOTICE, Citation, Finding, Verdict
from app.schemas.events import EARLIEST, LATEST, MAX_HEADCOUNT, EventFacts, VenueType
from app.schemas.money import MAX_CENTS
from app.services.money_check import money
from app.services.rule_engine import UnknownAttribute, build_packet, known_names

OptionId = Literal["in_kind_sponsor", "co_host", "fundraiser", "donations", "ticket_sales", "free_drawing",
                   "voluntary_dues", "other_usc_funds"]


@dataclass(frozen=True)
class _Option:
    id: OptionId
    title: str
    rule_id: str
    # The event activity this option adds; the obligations it brings are the option's steps and lead times.
    activity: str
    condition_rules: tuple[str, ...] = ()


OPTIONS: tuple[_Option, ...] = (
    _Option("in_kind_sponsor", "In-kind sponsorship (food, products or a venue)", "sponsorship-in-kind", "sponsorship",
            ("cosponsor-club-primary", "cosponsor-primary-audience", "sponsorship-cash-banned")),
    _Option("co_host", "Co-host with another recognized club", "cohost-recognized-club", "co_hosts",
            ("cohost-unrecognized-banned", "cosponsors-named-in-uepa")),
    _Option("fundraiser", "A fundraiser or sales", "fundraising-allowed", "fundraising",
            ("fundraising-approval-discretionary", "no-individual-benefit")),
    _Option("donations", "Donations through a University gift account", "donations-through-university", "fundraising",
            ("own-tax-exempt-banned",)),
    _Option("ticket_sales", "Ticket sales to cover this event's costs", "ticket-sales-cover-costs", "ticket_sales",
            ("usg-ineligible-ticketed-events", "cash-collection-approval")),
    _Option("free_drawing", "A free drawing (no purchase or donation needed)", "free-drawing-wording", "prize_drawing",
            ("raffle-purchase-banned",)),
    _Option("voluntary_dues", "Voluntary dues", "dues-voluntary", "collects_dues", ("dues-required-banned",)),
    _Option("other_usc_funds", "Other USC funds (a school council, department or grant)", "other-usc-funds-ask-usg",
            "other_usc_funding", ("usg-denial-other-university-funding",)),
)

# The ways a generic assistant suggests that USC does not allow (PROJECT_CONTEXT section 7, "Not allowed").
BANNED_RULES: tuple[str, ...] = ("sponsorship-cash-banned", "raffle-purchase-banned", "brand-ambassadors-banned",
                                 "sponsorship-activation-banned", "own-tax-exempt-banned")

# Words in the officer's own note that point at a banned idea; the matching rule is shown first, as "not allowed".
_IDEA_PATTERNS: dict[str, re.Pattern[str]] = {
    "sponsorship-cash-banned": re.compile(
        r"\b(cash|money|monetary|cheque|check|dollars?|wire|venmo|zelle|paypal|financial (?:support|contribution))\b.*\bsponsor|"
        r"\bsponsor\w*\b.*\b(cash|money|monetary|cheque|check|dollars?|pay(?:s|ing)? us|financial)\b|\$\s?\d.*\bsponsor|\bsponsor\w*\b.*\$\s?\d|"
        r"\b(company|companies|corporat\w*|brand|business\w*|firm)\b.*(\$\s?\d|\b(cash|money|dollars?|cheque|check)\b)|"
        r"(\$\s?\d|\b(cash|money|dollars?|cheque|check)\b).*\b(company|companies|corporat\w*|brand|business\w*|firm)\b|"
        r"\b(give|gives|giving|pay|pays|paying|write|send|wire|transfer)\b.{0,40}(\$\s?\d|\b(cash|money|cheque|check)\b)|"
        r"\b(would|will|could|to) pay (?:us|the club)\b|"
        r"\b(offer\w*|donat\w*)\b.{0,40}(\$\s?\d|\b(cash|money|cheque|check)\b)|\b(cash|monetary|money) (donations?|gifts?|sponsorships?)\b",
        re.IGNORECASE),
    "raffle-purchase-banned": re.compile(r"\b(raffles?|lottery|lotteries|sweepstakes?)\b", re.IGNORECASE),
    "brand-ambassadors-banned": re.compile(r"\b(brand ambassadors?|ambassador program|promoters?|influencers?)\b", re.IGNORECASE),
    "sponsorship-activation-banned": re.compile(
        r"\b(activations?|pop[- ]?ups?|product sampling|sampling (?:booth|table)|brand booth|samples?|(?:run|set up|have|host) (?:a|their|its) (?:booth|table|tent)|promo(?:tional)? (?:booth|table|tent))\b",
        re.IGNORECASE),
    "own-tax-exempt-banned": re.compile(r"\b(501\s?\(?c\)?\s?\(?3\)?|tax[- ]exempt|nonprofit status|non-profit status)\b", re.IGNORECASE),
}

# Anything in the drafted paragraph that asks for money or points at a banned option. Broad on purpose: a false match
# only means the paragraph is replaced by neutral words the officer can edit.
_EMAIL_BANNED = re.compile(
    r"\$|\b(cash|money|monetary|funds?|funding|fund(?:ed|ing)? us|donat\w*|contribut\w*|cheque|checks?|wire|venmo|zelle|"
    r"paypal|financial\w*|dollars?|pay(?:s|ing|ment)?|grant|budget|sponsorship (?:fee|package|tier|level)s?|tiers?|"
    r"raffles?|lotter\w*|sweepstakes?|prizes?|drawings?|tickets?|ambassadors?|promoters?|influencers?|activations?|"
    r"booths?|pop[- ]?ups?|sampl\w*|promot\w*|market\w*|advertis\w*|brand awareness|exposure|visibility|logo|"
    r"recruit\w*|sell\w*|sales?|vendor\w*)\b",
    re.IGNORECASE)

MAX_NOTE_CHARS = 2000
_DIGITS = re.compile(r"\d[\d,.]*")


class GapRequest(BaseModel):
    """The event and its shortfall. The shortfall comes from the year plan or money check (code), or the officer."""

    model_config = ConfigDict(extra="forbid")

    event_name: str = Field(default="", max_length=200)
    event_date: date | None = None
    venue: VenueType | None = None
    headcount: int | None = Field(default=None, ge=0, le=MAX_HEADCOUNT)
    attributes: list[str] = Field(default_factory=list, max_length=40)
    shortfall_cents: int = Field(default=0, ge=0, le=MAX_CENTS)
    # Whether the event also asks USG for money (ticket sales and other USC funds then need care).
    asks_usg: bool = False
    # What the officer has in mind, in their own words. Read by code for banned ideas; never followed.
    note: str = Field(default="", max_length=MAX_NOTE_CHARS)
    as_of: date | None = None

    @model_validator(mode="after")
    def _dates(self) -> GapRequest:
        if self.event_date is not None and not (EARLIEST <= self.event_date <= LATEST):
            raise ValueError(f"dates must be between {EARLIEST.year} and {LATEST.year}")
        return self


class OptionStep(BaseModel):
    rule_id: str
    title: str
    owner_office: str
    due: date | None
    due_note: str | None
    status_label: str
    past_due: bool
    citation: Citation


class GapOption(BaseModel):
    id: OptionId
    title: str
    # Allowed options are not pass/fail checks, so they carry no green. "allowed" or a yellow "check first".
    status: Literal["allowed", "check_first"]
    status_label: str
    message: str
    citation: Citation
    conditions: list[Citation]
    steps: list[OptionStep]
    lead_time: str
    finding: Finding | None
    can_draft_email: bool


class BannedOption(BaseModel):
    rule_id: str
    title: str
    why: str
    instead: str | None
    # True when the officer's own note mentions this idea.
    in_your_note: bool
    citation: Citation


class GapReport(BaseModel):
    as_of: date
    event_name: str
    shortfall_cents: int
    shortfall_text: str
    options: list[GapOption]
    not_allowed: list[BannedOption]
    notes: list[str]
    notice: str


def _lead_time(steps: list[OptionStep], event_date: date | None) -> str:
    dated = [s for s in steps if s.due is not None]
    if not steps:
        return "No form or approval of its own; the event's other steps still apply."
    if event_date is None:
        return "Enter the event date to see when each step is due."
    if not dated:
        return "Before the event (no fixed lead time in the rules)."
    first = min(dated, key=lambda s: s.due or event_date)
    days = (event_date - first.due).days if first.due else 0
    return f"Start by {first.due.isoformat() if first.due else ''}: {first.title} ({days} days before the event)."


def _steps(request: GapRequest, ruleset: RuleSet, calendar: AcademicCalendar, as_of: date, activity: str,
           baseline: set[str]) -> list[OptionStep]:
    facts = EventFacts(name=request.event_name or None, event_date=request.event_date, venue=request.venue,
                       headcount=request.headcount, attributes=sorted(set(request.attributes) | {activity}))
    packet = build_packet(facts, ruleset, calendar, as_of)
    out: list[OptionStep] = []
    for ob in packet.obligations:
        if activity not in ob.triggered_by or ob.rule_id in baseline or ob.superseded_by:
            continue
        if ruleset.get(ob.rule_id).kind not in ("deadline", "requirement"):
            continue
        out.append(OptionStep(rule_id=ob.rule_id, title=ob.title, owner_office=ob.owner_office, due=ob.due,
                              due_note=ob.due_note, status_label=ob.status_label, past_due=ob.past_due,
                              citation=ob.citation))
    out.sort(key=lambda s: (s.due is None, s.due or date.max, s.rule_id))
    return out


def ideas_in_note(note: str) -> set[str]:
    return {rule_id for rule_id, pattern in _IDEA_PATTERNS.items() if pattern.search(note)}


def funding_gap(request: GapRequest, ruleset: RuleSet, calendar: AcademicCalendar, as_of: date) -> GapReport:
    unknown = sorted(set(request.attributes) - known_names(ruleset))
    if unknown:
        raise UnknownAttribute(f"unknown attribute(s): {', '.join(unknown)}; use names from rules/vocabulary.json")
    base_facts = EventFacts(event_date=request.event_date, venue=request.venue, headcount=request.headcount,
                            attributes=list(request.attributes))
    baseline = {ob.rule_id for ob in build_packet(base_facts, ruleset, calendar, as_of).obligations}
    notes: list[str] = []
    options: list[GapOption] = []
    for opt in OPTIONS:
        rule = ruleset.get(opt.rule_id)
        steps = _steps(request, ruleset, calendar, as_of, opt.activity, baseline)
        conditions = [citation_for(ruleset, r) for r in opt.condition_rules if r in ruleset]
        finding: Finding | None = None
        status: Literal["allowed", "check_first"] = "allowed"
        if opt.id == "other_usc_funds":
            status = "check_first"
            finding = finding_for(ruleset, opt.rule_id, Verdict.YELLOW, rule.message, rule.fix_template)
        elif opt.id == "ticket_sales" and request.asks_usg:
            status = "check_first"
            finding = finding_for(ruleset, "usg-ineligible-ticketed-events", Verdict.YELLOW,
                                  "This event asks USG for money, and a ticketed event cannot get USG funding. Selling "
                                  "tickets would end the USG request.",
                                  "Choose another option, or drop the USG request and sell tickets only to cover costs.")
        options.append(GapOption(
            id=opt.id, title=opt.title, status=status,
            status_label="Allowed, with the conditions below" if status == "allowed" else "Needs a human look: check first",
            message=rule.message, citation=citation_for(ruleset, opt.rule_id), conditions=conditions, steps=steps,
            lead_time=_lead_time(steps, request.event_date), finding=finding,
            can_draft_email=opt.id in ("in_kind_sponsor", "co_host")))
    mentioned = ideas_in_note(request.note)
    banned = []
    for rule_id in BANNED_RULES:
        rule = ruleset.get(rule_id)
        banned.append(BannedOption(rule_id=rule_id, title=rule.title, why=rule.message, instead=rule.fix_template,
                                   in_your_note=rule_id in mentioned, citation=citation_for(ruleset, rule_id)))
    banned.sort(key=lambda b: not b.in_your_note)
    if mentioned:
        notes.append("Your note mentions something USC does not allow; it is listed first under 'Not allowed', with "
                     "what to do instead.")
    if request.shortfall_cents == 0:
        notes.append("No shortfall was given. The options are still listed.")
    return GapReport(as_of=as_of, event_name=request.event_name, shortfall_cents=request.shortfall_cents,
                     shortfall_text=money(request.shortfall_cents), options=options, not_allowed=banned, notes=notes,
                     notice=PRECHECK_NOTICE)


_FIGURE_WORDS = re.compile(r"\b(hundreds?|thousands?|millions?|dozens?|percent|dollars?|cents?)\b", re.IGNORECASE)


def figures_ok(paragraph: str, source: str) -> bool:
    """No figure the officer did not write: every number in digits must be in the officer's details, and no amount
    words. Small words such as 'one' or 'two' are allowed here: the email carries no budget figure."""
    allowed = {n.strip(",.") for n in _DIGITS.findall(source)}
    if not all(n.strip(",.") in allowed for n in _DIGITS.findall(paragraph)):
        return False
    return _FIGURE_WORDS.search(paragraph) is None


def email_is_clean(text: str) -> bool:
    return _EMAIL_BANNED.search(text) is None
