"""Money check types: a budget for one event (lines, event, club, attachments) and the report the money check
builds from it. Amounts are whole cents. Every figure in a report comes from code, never from the model."""

from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.common import Citation, Finding, Verdict
from app.schemas.events import EARLIEST, LATEST, MAX_HEADCOUNT, PacketObligation, VenueType

PurchaseChannel = Literal["vendor_quote", "online_cart", "amazon"]
Attachment = Literal[
    "esr",
    "hospitality_food_form",
    "food_health_permit_and_insurance",
    "food_justification",
    "statement_of_purpose",
    "traveler_information",
    "hotel_price_comparison",
    "hotel_point_of_contact",
    "lodging_justification",
]
FundId = Literal[
    "usg-fund-professional-academic",
    "usg-fund-philanthropy",
    "usg-fund-social-recreation-startup",
    "usg-fund-performing-visual-arts",
]
FUND_IDS: tuple[FundId, ...] = (
    "usg-fund-professional-academic",
    "usg-fund-philanthropy",
    "usg-fund-social-recreation-startup",
    "usg-fund-performing-visual-arts",
)
# Why a finding exists. "rule" means the rule named in the finding; the others are uncertainties, always yellow.
Reason = Literal["rule", "category_unclear", "duplicate_line", "totals_mismatch", "cannot_compute", "not_read"]

ATTACHMENT_LABELS: dict[str, str] = {
    "esr": "Event Status Report (ESR) from Trojan Event Services",
    "hospitality_food_form": "Hospitality's Food and Beverage form",
    "food_health_permit_and_insurance": "The food vendor's health permit and certificate of insurance",
    "food_justification": "Food justification",
    "statement_of_purpose": "Statement of purpose for the travel",
    "traveler_information": "Traveler details (name, date of birth, phone, USC email, USC ID, class level)",
    "hotel_price_comparison": "Hotel price comparison",
    "hotel_point_of_contact": "Hotel point of contact",
    "lodging_justification": "Lodging justification",
}

MAX_CENTS = 100_000_000_00  # $100 million: anything larger cannot be a club budget line
MAX_LINES = 200


class BudgetLine(BaseModel):
    """One expense, as the officer confirmed it (often pre-filled from a quote the model read)."""

    model_config = ConfigDict(extra="forbid")

    line: int = Field(ge=1, le=MAX_LINES)
    vendor: str = Field(default="", max_length=200)
    item: str = Field(default="", max_length=300)
    # A name from rules/vocabulary.json line_item_categories, or None when nobody knows yet.
    category: str | None = None
    # False when the category was read by the model with less than high confidence and the officer has not confirmed
    # it. An unsure category is never checked as if it were certain: the line is yellow, "needs a human look".
    category_sure: bool = True
    quantity: int = Field(ge=0, le=1_000_000)
    unit_price_cents: int = Field(ge=0, le=MAX_CENTS)
    amount_cents: int = Field(ge=0, le=MAX_CENTS)
    # For hotel rooms: the nights each room is booked. The quantity is rooms x nights and the unit price is one room
    # for one night.
    nights: int | None = Field(default=None, ge=1, le=366)
    has_quote: bool = False
    purchase_channel: PurchaseChannel = "vendor_quote"
    has_cart_screenshot: bool | None = None
    has_wish_list_link: bool | None = None
    # The uploaded document (1-based, in `documents`) this line comes from, if any.
    document: int | None = Field(default=None, ge=1, le=50)


class BudgetEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(default="", max_length=200)
    description: str = Field(default="", max_length=2000)
    event_date: date | None = None
    end_date: date | None = None
    expected_attendance: int | None = Field(default=None, ge=0, le=MAX_HEADCOUNT)
    venue: VenueType | None = None
    # None means the officer has not said; that is asked, never assumed.
    ticketed: bool | None = None
    open_to_all_students: bool | None = None
    # Other facts from rules/vocabulary.json the officer ticked (for example private_residence, international_travel,
    # other_usc_funding).
    attributes: list[str] = Field(default_factory=list, max_length=40)

    @model_validator(mode="after")
    def _dates(self) -> BudgetEvent:
        for day in (self.event_date, self.end_date):
            if day is not None and not EARLIEST <= day <= LATEST:
                raise ValueError(f"dates must be between {EARLIEST.year} and {LATEST.year}")
        if self.end_date is not None and self.event_date is None:
            raise ValueError("an end date needs a start date")
        if self.end_date is not None and self.event_date is not None:
            if self.end_date < self.event_date:
                raise ValueError("the event cannot end before it starts")
            if (self.end_date - self.event_date).days > 366:
                raise ValueError("an event can last at most a year")
        return self


class ClubMoney(BaseModel):
    model_config = ConfigDict(extra="forbid")

    # Money the club has already received from USG this academic year.
    usg_received_this_year_cents: int | None = Field(default=None, ge=0, le=MAX_CENTS)
    # Events of the club already funded by USG this semester.
    usg_funded_events_this_semester: int | None = Field(default=None, ge=0, le=1000)
    first_registered: date | None = None


class ReadLine(BaseModel):
    """A line the model read from a document, after code turned its text into numbers. Values the model was unsure
    of, or that code could not find written in the document, are None or listed in `unsure`."""

    item: str
    category: str | None
    category_sure: bool
    quantity: int | None
    unit_price_cents: int | None
    amount_cents: int | None
    nights: int | None
    is_fee: bool
    unsure: list[str]
    evidence: str | None


class QuoteDocument(BaseModel):
    """One uploaded quote, cart screenshot or invoice, as read by the model and checked by code."""

    index: int = Field(ge=1, le=50)
    name: str = Field(max_length=300)
    readable: bool
    vendor: str | None = Field(default=None, max_length=200)
    vendor_sure: bool = False
    kind: Literal["vendor_quote", "online_cart", "amazon", "invoice", "other"] = "other"
    currency_ok: bool = True
    currency_text: str | None = Field(default=None, max_length=40)
    lines: list[ReadLine] = Field(default_factory=list, max_length=200)
    stated_total_cents: int | None = Field(default=None, ge=0, le=MAX_CENTS)
    # Sum of every line and fee the model read, by code; None when any amount could not be read.
    read_total_cents: int | None = Field(default=None, ge=0)
    contains_instructions: bool = False
    notes: list[str] = Field(default_factory=list, max_length=60)


class FundReading(BaseModel):
    """Which fund the model thinks the event description fits. The model reads; code decides what to show."""

    fund: FundId | None
    confidence: Literal["high", "medium", "low"]
    also_fits: list[FundId] = Field(default_factory=list, max_length=4)
    evidence: str | None = Field(default=None, max_length=600)
    contains_instructions: bool = False


class MoneyCheckRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event: BudgetEvent
    club: ClubMoney = Field(default_factory=ClubMoney)
    attachments: list[Attachment] = Field(default_factory=list, max_length=20)
    lines: list[BudgetLine] = Field(min_length=1, max_length=MAX_LINES)
    documents: list[QuoteDocument] = Field(default_factory=list, max_length=50)
    # The fund the officer chose. When None, the fund reading (from the model) is used, and unsure means yellow.
    fund: FundId | None = None
    fund_reading: FundReading | None = None
    as_of: date | None = None

    @model_validator(mode="after")
    def _lines(self) -> MoneyCheckRequest:
        numbers = [line.line for line in self.lines]
        if len(set(numbers)) != len(numbers):
            raise ValueError("line numbers must be unique")
        indexes = {doc.index for doc in self.documents}
        for line in self.lines:
            if line.document is not None and line.document not in indexes:
                raise ValueError(f"line {line.line} points to document {line.document}, which is not in the request")
        return self


class MoneyFinding(BaseModel):
    reason: Reason
    finding: Finding


class VendorCheck(BaseModel):
    """Whether the vendor is on Greenlight's copy of USG's vendor list. Kept apart from the line's eligibility: being
    on the list never makes an expense eligible, and while the list is unconfirmed this check is always yellow."""

    status: Literal["on_list", "on_list_check_status", "not_on_list", "no_vendor"]
    listed_name: str | None
    list_note: str | None
    finding: Finding


class LineReport(BaseModel):
    line: int
    vendor: str
    item: str
    category: str | None
    category_label: str | None
    amount_cents: int
    verdict: Verdict
    verdict_label: str
    findings: list[MoneyFinding]
    # Rules this line was checked against and meets (green findings, each with its citation).
    passed: list[Finding]
    vendor_check: VendorCheck


class FundResult(BaseModel):
    fund: FundId | None
    fund_name: str | None
    # officer_chose: the officer picked it; matched: the description clearly fits; unsure: needs a human look.
    status: Literal["officer_chose", "matched", "unsure"]
    verdict: Verdict | None  # yellow when unsure; no verdict otherwise (a fund is a choice, not a pass)
    candidates: list[FundId]
    explanation: str
    citations: list[Citation]


class MoneyTotals(BaseModel):
    total_cents: int
    food_total_cents: int
    # Food per person, exact in cents when it divides evenly; otherwise None and `food_per_person_text` says
    # "about".
    food_per_person_cents: int | None
    food_per_person_text: str | None
    venue_personnel_cents: int
    usg_year_total_cents: int | None
    ineligible_cents: int


class MoneyReport(BaseModel):
    as_of: date
    verdict: Verdict
    verdict_label: str
    lines: list[LineReport]
    application: list[MoneyFinding]
    application_passed: list[Finding]
    # USG deadlines and blocked dates for this event, from the event packet's engine and deadline calculator.
    dates: list[PacketObligation]
    fund: FundResult
    totals: MoneyTotals
    documents: list[QuoteDocument]
    counts: dict[str, int]
    draft_allowed: bool
    draft_blocked_by: list[str]
    questions: list[str]
    notice: str
