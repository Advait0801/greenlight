"""The money check: a budget for one event + the rule table -> red, yellow or green per line, findings about the
application as a whole, the fund, the event's USG dates, and whether a draft may be written.

Pure Python. It never imports the AI client (tests/unit/test_architecture.py). Every sum, cap and per-person
figure is whole-cent integer arithmetic here; every limit is read from the rule's params; every finding is built
with app.rules.finding_for, so it carries the rule text and source and can never be a green the rule cannot
support. Dates come from the event packet's own engine (app.services.rule_engine.build_packet).
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import date

from app.rules import AcademicCalendar, RuleSet, citation_for, finding_for
from app.rules.schema import Rule
from app.schemas.common import PRECHECK_NOTICE, VERDICT_LABELS, Finding, Verdict
from app.schemas.events import EventFacts, PacketObligation
from app.schemas.money import (
    ATTACHMENT_LABELS,
    FUND_IDS,
    BudgetLine,
    FundId,
    FundReading,
    FundResult,
    LineReport,
    MoneyCheckRequest,
    MoneyFinding,
    MoneyReport,
    MoneyTotals,
    QuoteDocument,
    Reason,
    VendorCheck,
)
from app.services.rule_engine import build_packet
from app.services.vendor_list import ListedVendor, find_vendor, normalize_name

ORDER = {Verdict.GREEN: 0, Verdict.YELLOW: 1, Verdict.OFFICE_DECIDES: 2, Verdict.RED: 3}
ON_CAMPUS = {"venue_tes_meeting_room", "venue_tes_large", "venue_outdoor", "venue_classroom"}
TRAVEL_CATEGORIES = {"airfare", "ground_transport", "lodging"}
# Lines the Performing and Visual Arts Fund pays only from a PO vendor (rule usg-pva-po-vendor).
PRODUCTION_CATEGORIES = {"venue_rental", "personnel", "security", "av_equipment", "decorations"}
# Documents a rule requires, by rule id (the attachment names are the test set's and the page's).
ATTACHMENT_RULES = {
    "usg-esr-on-campus": "esr",
    "usg-hospitality-food-form": "hospitality_food_form",
    "usg-food-health-permit-insurance": "food_health_permit_and_insurance",
    "usg-food-justification": "food_justification",
    "usg-travel-statement-of-purpose": "statement_of_purpose",
    "usg-traveler-information": "traveler_information",
    "usg-hotel-price-comparison": "hotel_price_comparison",
    "usg-hotel-point-of-contact": "hotel_point_of_contact",
    "usg-lodging-justification": "lodging_justification",
}
UNCLEAR_RULE = "usg-ineligible-expenses-list"
EVENT_ATTRIBUTE_GROUPS = ("event_attributes", "facts", "application_facts")


class UnknownName(ValueError):
    """A category or event detail that is not in rules/vocabulary.json."""


def money(cents: int) -> str:
    sign = "-" if cents < 0 else ""
    whole, part = divmod(abs(cents), 100)
    return f"{sign}${whole:,}.{part:02d}"


def _ceil_div(a: int, b: int) -> int:
    return -(-a // b)


def _worst(verdicts: Iterable[Verdict]) -> Verdict:
    return max(verdicts, key=ORDER.__getitem__, default=Verdict.GREEN)


def _fill(template: str | None, **values: str) -> str | None:
    """A rule's fix_template with its {placeholders} filled by code. None if a placeholder has no value."""
    if not template:
        return None
    try:
        return template.format(**values)
    except (KeyError, IndexError, ValueError):
        return None


@dataclass
class _Builder:
    ruleset: RuleSet

    def finding(self, rule_id: str, verdict: Verdict, message: str, fix: str | None = None) -> Finding:
        """A finding from the rule table. If the rule cannot carry this verdict (an unverified rule cannot be a
        certain red), it is shown yellow instead, never upgraded."""
        try:
            return finding_for(self.ruleset, rule_id, verdict, message, fix)
        except ValueError:
            return finding_for(self.ruleset, rule_id, Verdict.YELLOW, message, fix)

    def item(self, rule_id: str, verdict: Verdict, message: str, fix: str | None = None, reason: Reason = "rule") -> MoneyFinding:
        if reason != "rule":
            verdict = Verdict.YELLOW
        return MoneyFinding(reason=reason, finding=self.finding(rule_id, verdict, message, fix))

    def passed(self, rule_id: str, message: str) -> Finding | None:
        """A green finding for a rule the item meets, or None if the rule cannot be a pass."""
        try:
            return finding_for(self.ruleset, rule_id, Verdict.GREEN, message)
        except ValueError:
            return None


@dataclass
class _Line:
    line: BudgetLine
    findings: list[MoneyFinding] = field(default_factory=list)
    passed: list[Finding] = field(default_factory=list)


def _limit_cents(rule: Rule, key: str) -> int:
    value = rule.params[key]
    return int(round(float(value) * 100))


# Public name for other engines (the year planner) that read a cap from the same rule params.
limit_cents = _limit_cents


def _category_label(ruleset: RuleSet, category: str | None) -> str | None:
    if category is None:
        return None
    return ruleset.vocabulary.get("line_item_categories", {}).get(category, category)


def _what(line: BudgetLine) -> str:
    return line.item or line.vendor or f"line {line.line}"


def _validate_names(request: MoneyCheckRequest, ruleset: RuleSet) -> None:
    categories = ruleset.vocabulary.get("line_item_categories", {})
    bad = sorted({line.category for line in request.lines if line.category is not None and line.category not in categories})
    if bad:
        raise UnknownName(f"unknown categor{'y' if len(bad) == 1 else 'ies'}: {', '.join(bad)}; use names from rules/vocabulary.json")
    known = {name for group in EVENT_ATTRIBUTE_GROUPS for name in ruleset.vocabulary.get(group, {})}
    bad = sorted(set(request.event.attributes) - known)
    if bad:
        raise UnknownName(f"unknown event detail(s): {', '.join(bad)}; use names from rules/vocabulary.json")


def link_documents(lines: list[BudgetLine], documents: list[QuoteDocument]) -> dict[int, int]:
    """line number -> document index: the document the officer linked, or else the one document whose vendor (read
    with high confidence) has the same name as the line's vendor."""
    links: dict[int, int] = {}
    by_vendor: dict[str, list[int]] = {}
    for doc in documents:
        if doc.vendor and doc.vendor_sure:
            by_vendor.setdefault(normalize_name(doc.vendor), []).append(doc.index)
    for line in lines:
        if line.document is not None:
            links[line.line] = line.document
            continue
        matches = by_vendor.get(normalize_name(line.vendor), []) if line.vendor else []
        if len(matches) == 1:
            links[line.line] = matches[0]
    return links


# ---------------------------------------------------------------------------------------------------------------
# Line checks


def _check_amount(b: _Builder, entry: _Line) -> None:
    line = entry.line
    if line.quantity * line.unit_price_cents != line.amount_cents:
        entry.findings.append(b.item(
            "usg-quote-required", Verdict.YELLOW,
            f"{line.quantity} x {money(line.unit_price_cents)} is {money(line.quantity * line.unit_price_cents)}, "
            f"but the line says {money(line.amount_cents)}. Check the line against its quote.",
            "Correct the quantity, the unit price or the amount so they agree with the quote.",
            reason="totals_mismatch",
        ))


def _check_category(b: _Builder, ruleset: RuleSet, entry: _Line) -> bool:
    """False when the category is unknown or unsure: the line then needs a human look and cannot be green."""
    line = entry.line
    if line.category is None or line.category == "other":
        entry.findings.append(b.item(
            UNCLEAR_RULE, Verdict.YELLOW,
            f"'{_what(line)}' does not say clearly what is being bought; needs a human look.",
            ruleset.get(UNCLEAR_RULE).fix_template, reason="category_unclear",
        ))
        return False
    if not line.category_sure:
        entry.findings.append(b.item(
            UNCLEAR_RULE, Verdict.YELLOW,
            f"Greenlight is not sure '{_what(line)}' is {_category_label(ruleset, line.category)!r}; needs a human look.",
            "Confirm or change the category, then run the check again.", reason="category_unclear",
        ))
        return False
    return True


def _check_ineligible(b: _Builder, ruleset: RuleSet, entry: _Line, sure: bool) -> None:
    line = entry.line
    if line.category is None:
        return
    for rule in ruleset:
        if rule.domain != "funding" or rule.kind != "ineligible" or line.category not in (rule.triggers or []):
            continue
        fix = _fill(rule.fix_template, item=_what(line), vendor=line.vendor or "the vendor") or (
            f"Remove {_what(line)} ({money(line.amount_cents)}) from the USG request and pay for it another way."
        )
        if sure:
            message = f"{_what(line)} ({money(line.amount_cents)}): {rule.message}"
            entry.findings.append(b.item(rule.id, Verdict.RED, message, fix))
        else:
            message = f"If this is {_category_label(ruleset, line.category)!r}, USG does not fund it: {rule.message}"
            entry.findings.append(b.item(rule.id, Verdict.YELLOW, message, fix))


def _check_office(b: _Builder, ruleset: RuleSet, entry: _Line) -> None:
    line = entry.line
    for rule in ruleset:
        if (rule.domain == "funding" and rule.kind == "requirement" and rule.severity == "office_decides"
                and line.category in (rule.triggers or [])):
            entry.findings.append(b.item(rule.id, Verdict.OFFICE_DECIDES, rule.message, _fill(rule.fix_template)))


def _check_documents_for_line(b: _Builder, entry: _Line) -> None:
    line = entry.line
    what = _what(line)
    if not line.has_quote:
        entry.findings.append(b.item(
            "usg-quote-required", Verdict.RED, f"No quote is attached for {what}.",
            _fill(b.ruleset.get("usg-quote-required").fix_template, vendor=line.vendor or "the vendor", item=what),
        ))
    else:
        ok = b.passed("usg-quote-required", f"A quote is attached for {what}.")
        if ok:
            entry.passed.append(ok)
    if line.purchase_channel == "online_cart":
        if line.has_cart_screenshot:
            ok = b.passed("usg-cart-screenshot", f"A cart screenshot is attached for {what}.")
            if ok:
                entry.passed.append(ok)
        else:
            entry.findings.append(b.item(
                "usg-cart-screenshot", Verdict.RED, f"{what} is bought online, and no cart screenshot is attached.",
                _fill(b.ruleset.get("usg-cart-screenshot").fix_template, item=what),
            ))
    elif line.purchase_channel == "amazon":
        if line.has_wish_list_link:
            ok = b.passed("usg-amazon-wishlist", f"An Amazon wish list link is given for {what}.")
            if ok:
                entry.passed.append(ok)
        else:
            rule = b.ruleset.get("usg-amazon-wishlist")
            entry.findings.append(b.item(
                "usg-amazon-wishlist", Verdict.RED, f"{what} is bought on Amazon, and no wish list link is given.",
                _fill(rule.fix_template, item=what) or "Add the Amazon wish list link.",
            ))


def _check_hotel(b: _Builder, ruleset: RuleSet, entry: _Line) -> None:
    line = entry.line
    rule = ruleset.get("usg-hotel-cap")
    cap = _limit_cents(rule, "max_usd_per_night")
    if line.nights is None:
        entry.findings.append(b.item(
            rule.id, Verdict.YELLOW,
            "The number of nights is not given, so Greenlight cannot tell the price of one room for one night.",
            "Enter the nights, with the quantity as rooms x nights and the unit price as one room for one night.",
            reason="cannot_compute",
        ))
        return
    per_night = line.unit_price_cents
    rooms_times_nights = line.quantity % line.nights == 0 and line.quantity > 0
    if not rooms_times_nights:
        entry.findings.append(b.item(
            rule.id, Verdict.YELLOW,
            f"The quantity ({line.quantity}) is not rooms x nights for {line.nights} nights, so the unit price may not be "
            "one room for one night.",
            "Enter the quantity as rooms x nights and the unit price as one room for one night.", reason="cannot_compute"))
    if per_night > cap:
        entry.findings.append(b.item(
            rule.id, Verdict.RED, f"{money(per_night)} per night; the cap is {money(cap)}.",
            _fill(rule.fix_template, per_night=money(per_night)[1:]) or f"Choose a room at or under {money(cap)} per night.",
        ))
    elif rooms_times_nights:
        ok = b.passed(rule.id, f"{money(per_night)} per night is within the {money(cap)} cap.")
        if ok:
            entry.passed.append(ok)


def _check_duplicates(b: _Builder, entries: list[_Line]) -> None:
    seen: dict[tuple[str, str, int], int] = {}
    for entry in entries:
        line = entry.line
        key = (normalize_name(line.vendor), " ".join(line.item.lower().split()), line.amount_cents)
        if not key[0] and not key[1]:
            continue
        first = seen.get(key)
        if first is None:
            seen[key] = line.line
            continue
        entry.findings.append(b.item(
            "usg-quote-required", Verdict.YELLOW,
            f"Same vendor, item and amount ({money(line.amount_cents)}) as line {first}: possibly entered twice.",
            f"Delete this line if it repeats line {first}, or attach the quote that covers both.",
            reason="duplicate_line",
        ))


def _vendor_check(b: _Builder, line: BudgetLine, vendors: tuple[ListedVendor, ...]) -> VendorCheck:
    rule_id = "usg-approved-vendor"
    if not line.vendor.strip():
        return VendorCheck(status="no_vendor", listed_name=None, list_note=None, finding=b.finding(
            rule_id, Verdict.YELLOW, "No vendor is named for this line; USG pays listed vendors directly.",
            "Name the vendor, then check it against USG's vendor list."))
    listed = find_vendor(line.vendor, vendors)
    if listed is None:
        return VendorCheck(status="not_on_list", listed_name=None, list_note=None, finding=b.finding(
            rule_id, Verdict.YELLOW,
            f"'{line.vendor}' was not found on Greenlight's copy of USG's vendor list. USG does not accept a vendor "
            "that is not on its list, but the list changes and is not complete.",
            _fill(b.ruleset.get(rule_id).fix_template, vendor=line.vendor)))
    if listed.needs_status_check:
        return VendorCheck(status="on_list_check_status", listed_name=listed.name, list_note=listed.note, finding=b.finding(
            rule_id, Verdict.YELLOW,
            f"'{line.vendor}' is on USG's vendor list ({listed.tab}) with the note '{listed.note}': its status needs a check.",
            "Confirm the vendor's status with USG (usgfunds@usc.edu) or Purchasing Services before applying."))
    return VendorCheck(status="on_list", listed_name=listed.name, list_note=listed.note or None, finding=b.finding(
        rule_id, Verdict.YELLOW,
        f"'{line.vendor}' is on Greenlight's copy of USG's vendor list ({listed.tab}). The list changes; confirm before "
        "applying. Being on the list does not make the expense eligible.",
        "Confirm the vendor's status with USG before applying."))


# ---------------------------------------------------------------------------------------------------------------
# Fund


def _fund_name(ruleset: RuleSet, fund: FundId) -> str:
    return str(ruleset.get(fund).params.get("fund", ruleset.get(fund).title))


def match_fund(ruleset: RuleSet, chosen: FundId | None, reading: FundReading | None) -> FundResult:
    """The fund to show: the officer's choice, or the model's reading only when it is sure and names one fund.
    Anything else is yellow, with the candidates."""
    if chosen is not None:
        return FundResult(fund=chosen, fund_name=_fund_name(ruleset, chosen), status="officer_chose", verdict=None,
                          candidates=[chosen], explanation="You chose this fund.", citations=[citation_for(ruleset, chosen)])
    if (reading is not None and reading.fund is not None and reading.confidence == "high" and not reading.also_fits
            and not reading.contains_instructions):
        fund = reading.fund
        why = f"The event description fits this fund ({reading.evidence})." if reading.evidence else "The event description fits this fund."
        return FundResult(fund=fund, fund_name=_fund_name(ruleset, fund), status="matched", verdict=None, candidates=[fund],
                          explanation=why + " Check it against the fund's description before applying.",
                          citations=[citation_for(ruleset, fund)])
    candidates: list[FundId] = []
    if reading is not None:
        for fund in ([reading.fund] if reading.fund else []) + list(reading.also_fits):
            if fund in FUND_IDS and fund not in candidates:
                candidates.append(fund)
    if not candidates:
        candidates = list(FUND_IDS)
    if reading is None:
        why = "Greenlight could not read which fund fits; choose the fund yourself."
    elif reading.contains_instructions:
        why = ("The event description contains words that read like instructions, so Greenlight does not trust its own "
               "reading of the fund; needs a human look. Choose the fund yourself.")
    else:
        why = "Greenlight is not sure which fund fits this event; needs a human look. Choose the fund yourself."
    return FundResult(fund=None, fund_name=None, status="unsure", verdict=Verdict.YELLOW, candidates=candidates,
                      explanation=why, citations=[citation_for(ruleset, fund) for fund in candidates])


# ---------------------------------------------------------------------------------------------------------------
# The whole check


def _usg_dates(request: MoneyCheckRequest, ruleset: RuleSet, calendar: AcademicCalendar, as_of: date,
               names: set[str]) -> tuple[list[PacketObligation], list[str]]:
    """USG deadlines and blocked dates for this event, from the event packet's engine (never computed here)."""
    event = request.event
    attributes = sorted({"usg_funding", *(n for n in names if n in ruleset.vocabulary.get("event_attributes", {}))}
                        - {"venue_tes_meeting_room", "venue_tes_large", "venue_outdoor", "venue_classroom", "venue_off_campus"})
    facts = EventFacts(name=event.name or None, event_date=event.event_date,
                       end_date=event.end_date if event.end_date != event.event_date else None,
                       venue=event.venue, headcount=event.expected_attendance, attributes=attributes)
    packet = build_packet(facts, ruleset, calendar, as_of)
    kept = [o for o in packet.obligations
            if ruleset.get(o.rule_id).domain == "funding" and ruleset.get(o.rule_id).kind in ("deadline", "blocked_period")]
    blocks: list[str] = []
    if event.event_date is not None and event.event_date < as_of:
        blocks.append(f"The event date, {event.event_date.isoformat()}, has already passed.")
    for o in kept:
        if o.superseded_by is not None:
            continue
        if o.status == "blocked":
            blocks.append(f"{o.title}: {o.note or o.message}")
        elif o.past_due:
            blocks.append(f"{o.title}: the deadline has passed. {o.note or ''}".strip())
    return kept, blocks


def check_budget(request: MoneyCheckRequest, ruleset: RuleSet, calendar: AcademicCalendar, as_of: date,
                 vendors: tuple[ListedVendor, ...] = ()) -> MoneyReport:
    _validate_names(request, ruleset)
    b = _Builder(ruleset)
    event, club = request.event, request.club
    entries = [_Line(line) for line in sorted(request.lines, key=lambda line: line.line)]
    application: list[MoneyFinding] = []
    app_passed: list[Finding] = []
    questions: list[str] = []

    # ---- per-line checks
    for entry in entries:
        _check_amount(b, entry)
        sure = _check_category(b, ruleset, entry)
        _check_ineligible(b, ruleset, entry, sure)
        if sure:
            _check_office(b, ruleset, entry)
            if entry.line.category == "lodging":
                _check_hotel(b, ruleset, entry)
            if entry.line.category == "t_shirts":
                rule = ruleset.get("usg-tshirts-licensed-vendor")
                entry.findings.append(b.item(rule.id, Verdict.YELLOW,
                                             f"Greenlight cannot check whether {entry.line.vendor or 'the vendor'} is authorized by "
                                             "USC Trademarks and Licensing; needs a human look.", rule.fix_template))
        _check_documents_for_line(b, entry)
    _check_duplicates(b, entries)

    sure_lines = [e.line for e in entries if e.line.category_sure and e.line.category not in (None, "other")]
    total = sum(e.line.amount_cents for e in entries)
    categories = {line.category for line in sure_lines}
    unsure_categories = {e.line.category for e in entries if not e.line.category_sure and e.line.category}

    # ---- food: $35 per person over all food lines, on expected attendance
    food_rule = ruleset.get("usg-food-cap")
    food_cap = _limit_cents(food_rule, "max_usd_per_person")
    food_entries = [e for e in entries if e.line.category == "food" and e.line.category_sure]
    food_total = sum(e.line.amount_cents for e in food_entries)
    attendance = event.expected_attendance
    food_pp: int | None = None
    food_pp_text: str | None = None
    if food_entries:
        if not attendance:
            note = ("Expected attendance is 0, so food per person cannot be computed. Enter the expected attendance."
                    if attendance == 0 else
                    "Expected attendance is not given, so food per person cannot be computed. Enter the expected attendance.")
            for entry in food_entries:
                entry.findings.append(b.item(food_rule.id, Verdict.YELLOW, note, "Enter the expected attendance.", reason="cannot_compute"))
        else:
            exact = food_total % attendance == 0
            food_pp = food_total // attendance if exact else None
            over = food_total - food_cap * attendance
            if exact:
                food_pp_text = money(food_total // attendance)
            elif over > 0:
                food_pp_text = f"more than {money(food_total // attendance)}"
            else:
                food_pp_text = f"about {money(food_total // attendance)}"
            if over > 0:
                min_people = _ceil_div(food_total, food_cap)
                shown = money(food_total // attendance) if exact else f"more than {money(food_cap)}"
                message = (f"{shown} per person; the cap is {money(food_cap)} (over by {money(over)} for {attendance} people)."
                           if exact else
                           f"{money(food_total)} for {attendance} people is more than {money(food_cap)} per person "
                           f"(over by {money(over)}).")
                fix = (f"Food is {shown} per person; the cap is {money(food_cap)}. Cut {money(over)}, or plan for at least "
                       f"{min_people} people.")
                for entry in food_entries:
                    entry.findings.append(b.item(food_rule.id, Verdict.RED, message, fix))
            else:
                for entry in food_entries:
                    ok = b.passed(food_rule.id, f"Food is {food_pp_text} per person, within the {money(food_cap)} cap "
                                  f"({money(food_total)} for {attendance} people).")
                    if ok:
                        entry.passed.append(ok)

    # ---- on-campus venue and personnel: USG pays up to $4,000
    vp_rule = ruleset.get("usg-venue-personnel-cap")
    vp_cap = _limit_cents(vp_rule, "max_usd")
    vp_categories = set(vp_rule.params.get("categories", []))
    vp_entries = [e for e in entries if e.line.category in vp_categories and e.line.category_sure]
    vp_total = sum(e.line.amount_cents for e in vp_entries)
    if vp_entries:
        if vp_total > vp_cap:
            over = vp_total - vp_cap
            for entry in vp_entries:
                entry.findings.append(b.item(
                    vp_rule.id, Verdict.RED,
                    f"Venue and personnel total {money(vp_total)}; USG covers up to {money(vp_cap)}.",
                    f"You are asking USG for {money(vp_total)} for venue and personnel. USG covers up to {money(vp_cap)}; "
                    f"ask for {money(over)} less and cover the rest another way."))
        else:
            for entry in vp_entries:
                ok = b.passed(vp_rule.id, f"Venue and personnel total {money(vp_total)}, within the {money(vp_cap)} USG covers.")
                if ok:
                    entry.passed.append(ok)

    if event.venue == "venue_off_campus":
        for entry in entries:
            if entry.line.category in ("venue_rental", "personnel"):
                entry.findings.append(b.item(
                    vp_rule.id, Verdict.YELLOW,
                    f"{_what(entry.line)} is on-campus {'venue rental' if entry.line.category == 'venue_rental' else 'staffing'}, "
                    "but the event is marked off campus; needs a human look.",
                    "Correct the venue or the line's category, then run the check again."))

    # ---- vendor checks (separate from eligibility)
    vendor_checks = {e.line.line: _vendor_check(b, e.line, vendors) for e in entries}

    # ---- the event as a whole
    names: set[str] = set(event.attributes) | categories
    if event.venue:
        names.add(event.venue)
    if categories & TRAVEL_CATEGORIES:
        names.add("travel")
    if "lodging" in categories:
        names.add("lodging")
    if event.end_date is not None and event.event_date is not None and event.end_date > event.event_date:
        names.add("multi_day")
    if event.ticketed:
        names.add("ticket_sales")
    on_campus = event.venue in ON_CAMPUS
    if event.open_to_all_students is False and on_campus:
        names.add("not_open_to_all_students")

    # Ineligible events (ticket sales, closed on-campus events, private residences, international travel).
    for rule in ruleset:
        if rule.domain != "funding" or rule.kind != "ineligible":
            continue
        triggers = set(rule.triggers or [])
        if triggers & names and not triggers & set(ruleset.vocabulary.get("line_item_categories", {})):
            detail = {
                "usg-ineligible-ticketed-events": "The event sells tickets.",
                "usg-ineligible-closed-on-campus-events": "The event is on campus and not open to all students.",
            }.get(rule.id, "")
            application.append(b.item(rule.id, Verdict.RED, f"{detail} {rule.message}".strip(), _fill(rule.fix_template)))
    if event.ticketed is None:
        questions.append("Does the event sell tickets or charge an entry fee? USG does not fund events with ticket sales.")
        application.append(b.item("usg-ineligible-ticketed-events", Verdict.YELLOW,
                                  "Greenlight does not know whether the event sells tickets; USG does not fund events with "
                                  "ticket sales. Needs your answer."))
    if event.open_to_all_students is None and (on_campus or event.venue is None):
        questions.append("Is the event open to all students? USG does not fund on-campus events that are not.")
        application.append(b.item("usg-ineligible-closed-on-campus-events", Verdict.YELLOW,
                                  "Greenlight does not know whether the event is open to all students; USG does not fund "
                                  "on-campus events that are not. Needs your answer."))
    elif event.open_to_all_students is False and event.venue is None:
        application.append(b.item("usg-ineligible-closed-on-campus-events", Verdict.YELLOW,
                                  "The event is not open to all students. If it is on campus, USG does not fund it; give the venue."))

    # Required documents.
    for rule_id, attachment in ATTACHMENT_RULES.items():
        if rule_id not in ruleset:
            continue
        rule = ruleset.get(rule_id)
        triggers = set(rule.triggers or [])
        label = ATTACHMENT_LABELS[attachment]
        if triggers & names:
            if attachment in request.attachments:
                ok = b.passed(rule_id, f"Attached: {label}.")
                if ok:
                    app_passed.append(ok)
            else:
                application.append(b.item(rule_id, Verdict.RED, f"Not attached: {label}. {rule.message}", _fill(rule.fix_template, missing_fields="all of them")))
        elif rule_id == "usg-esr-on-campus" and event.venue is None and attachment not in request.attachments:
            application.append(b.item(rule_id, Verdict.YELLOW,
                                      f"The venue is not given. If the event is on campus, attach the {label}.",
                                      _fill(rule.fix_template)))
        elif triggers & unsure_categories and attachment not in request.attachments:
            application.append(b.item(rule_id, Verdict.YELLOW,
                                      f"If an unsure line is {', '.join(sorted(triggers & unsure_categories))}, attach the {label}.",
                                      _fill(rule.fix_template)))

    # Over $4,000 and multi-day events: the office decides.
    over_rule = ruleset.get("usg-over-4000-case-by-case")
    if total > _limit_cents(over_rule, "threshold_usd"):
        application.append(b.item(over_rule.id, Verdict.OFFICE_DECIDES,
                                  f"Event expenses total {money(total)}. {over_rule.message}", _fill(over_rule.fix_template)))
    if "multi_day" in names:
        rule = ruleset.get("usg-multi-day-case-by-case")
        application.append(b.item(rule.id, Verdict.OFFICE_DECIDES, rule.message, _fill(rule.fix_template)))

    # $8,000 a year.
    year_rule = ruleset.get("usg-yearly-cap")
    year_cap = _limit_cents(year_rule, "max_usd_per_year")
    year_total: int | None = None
    if club.usg_received_this_year_cents is None:
        questions.append("How much has the club already received from USG this academic year?")
        application.append(b.item(year_rule.id, Verdict.YELLOW,
                                  f"Greenlight does not know how much the club has received from USG this year, so it cannot "
                                  f"check the {money(year_cap)} yearly cap.", "Enter the amount received this year.",
                                  reason="cannot_compute"))
    else:
        year_total = club.usg_received_this_year_cents + total
        if year_total > year_cap:
            over = year_total - year_cap
            application.append(b.item(
                year_rule.id, Verdict.RED,
                f"Already received {money(club.usg_received_this_year_cents)}; this request of {money(total)} makes "
                f"{money(year_total)}, over by {money(over)}.",
                f"This request would bring the year's USG total to {money(year_total)}. Cut {money(over)} or fund it another way."))
        else:
            ok = b.passed(year_rule.id, f"With this request the club's USG total for the year is {money(year_total)}, within "
                          f"{money(year_cap)}.")
            if ok:
                app_passed.append(ok)

    # Up to 4 funded events a semester (unconfirmed: always yellow).
    sem_rule = ruleset.get("usg-events-per-semester-cap")
    sem_cap = int(sem_rule.params["max_funded_events_per_semester"])
    if club.usg_funded_events_this_semester is None:
        questions.append("How many of the club's events has USG already funded this semester?")
    elif club.usg_funded_events_this_semester >= sem_cap:
        nth = club.usg_funded_events_this_semester + 1
        application.append(b.item(sem_rule.id, Verdict.YELLOW,
                                  f"This would be the club's funded event number {nth} this semester; the {sem_cap}-event limit "
                                  "is on the USG web page but not in the guidelines.", sem_rule.fix_template))

    # Yellow notes that need a person: conference logins, the event ID, other University money.
    if "registration_fee" in categories and "usg-conference-logins" in ruleset:
        rule = ruleset.get("usg-conference-logins")
        application.append(b.item(rule.id, Verdict.YELLOW, rule.message, _fill(rule.fix_template)))
    if on_campus and "usg-uepa-event-id" in ruleset:
        rule = ruleset.get("usg-uepa-event-id")
        application.append(b.item(rule.id, Verdict.YELLOW, rule.message, _fill(rule.fix_template)))
    if "other_usc_funding" in names:
        rule = ruleset.get("usg-denial-other-university-funding")
        application.append(b.item(rule.id, Verdict.YELLOW, rule.message, _fill(rule.fix_template)))

    # ---- uploaded documents against the budget
    links = link_documents([e.line for e in entries], request.documents)
    for doc in request.documents:
        linked = [e.line for e in entries if links.get(e.line.line) == doc.index]
        rule_id = "usg-cart-screenshot" if doc.kind in ("online_cart", "amazon") else "usg-quote-required"
        name = doc.vendor or doc.name
        if not doc.readable:
            application.append(b.item("usg-quote-required", Verdict.YELLOW,
                                      f"Greenlight could not read '{doc.name}'. Check its lines by hand.",
                                      "Upload a clearer copy, or type the lines in.", reason="not_read"))
            continue
        if not doc.currency_ok:
            application.append(b.item("usg-quote-required", Verdict.YELLOW,
                                      f"'{doc.name}' shows amounts in {doc.currency_text or 'another currency'}, not US dollars; "
                                      "Greenlight checks dollar amounts only.",
                                      "Enter the dollar amount the vendor will charge, with a quote in dollars.",
                                      reason="totals_mismatch"))
        if doc.stated_total_cents is not None and doc.read_total_cents is not None and doc.stated_total_cents != doc.read_total_cents:
            application.append(b.item(rule_id, Verdict.YELLOW,
                                      f"'{doc.name}' states a total of {money(doc.stated_total_cents)}, but its lines and fees add "
                                      f"up to {money(doc.read_total_cents)}.",
                                      "Check the document's lines and total by hand.", reason="totals_mismatch"))
        document_total = doc.stated_total_cents if doc.stated_total_cents is not None else doc.read_total_cents
        if linked and document_total is not None:
            budget = sum(line.amount_cents for line in linked)
            if budget != document_total:
                where = "The cart" if doc.kind == "online_cart" else "The document"
                extra = "; fees or shipping may be missing from the budget" if budget < document_total else ""
                application.append(b.item(
                    rule_id, Verdict.YELLOW,
                    f"{where} from {name} totals {money(document_total)} but the budget lists {money(budget)}{extra}.",
                    "Make the budget lines match the quote, including every fee.", reason="totals_mismatch"))
        if not linked:
            application.append(b.item(rule_id, Verdict.YELLOW,
                                      f"No budget line is linked to '{doc.name}' ({name}), so Greenlight could not compare it "
                                      "with the budget; needs a human look.",
                                      "Link the document to its budget lines, or check its total and fees by hand."))
        if doc.contains_instructions:
            questions.append(f"'{doc.name}' contains words that read like instructions. Greenlight treated them as text and did not follow them.")

    # ---- fund
    fund = match_fund(ruleset, request.fund, request.fund_reading)
    chosen = fund.fund
    if chosen == "usg-fund-professional-academic":
        rule = ruleset.get("usg-professional-free-open")
        if event.ticketed or event.open_to_all_students is False:
            application.append(b.item(rule.id, Verdict.RED, rule.message, _fill(rule.fix_template)))
        elif event.ticketed is None or event.open_to_all_students is None:
            application.append(b.item(rule.id, Verdict.YELLOW, rule.message + " Confirm both.", _fill(rule.fix_template)))
        else:
            ok = b.passed(rule.id, "The event is free and open to all students.")
            if ok:
                app_passed.append(ok)
    elif chosen == "usg-fund-performing-visual-arts":
        rule = ruleset.get("usg-pva-po-vendor")
        production = [e.line for e in entries if e.line.category in PRODUCTION_CATEGORIES]
        if production:
            listed = ", ".join(f"line {line.line} ({_what(line)})" for line in production)
            application.append(b.item(rule.id, Verdict.YELLOW,
                                      f"Greenlight cannot check whether these are bought from a PO vendor: {listed}. "
                                      "Needs a human look.", "Use a PO vendor for each of these lines."))
    elif chosen == "usg-fund-philanthropy":
        rule = ruleset.get("usg-philanthropy-no-service-payments")
        application.append(b.item(rule.id, Verdict.YELLOW,
                                  rule.message + " Greenlight cannot tell whether a line pays for a service on behalf of a "
                                  "non-profit; needs a human look.", "Remove any such line, or have the non-profit pay for it."))

    # ---- USG dates from the event packet's engine
    dates, hard_blocks = _usg_dates(request, ruleset, calendar, as_of, names)

    # ---- the report
    line_reports: list[LineReport] = []
    for entry in entries:
        verdict = _worst(f.finding.verdict for f in entry.findings)
        line_reports.append(LineReport(
            line=entry.line.line, vendor=entry.line.vendor, item=entry.line.item, category=entry.line.category,
            category_label=_category_label(ruleset, entry.line.category), amount_cents=entry.line.amount_cents,
            verdict=verdict, verdict_label=VERDICT_LABELS[verdict], findings=entry.findings, passed=entry.passed,
            vendor_check=vendor_checks[entry.line.line]))

    date_verdicts = [o.finding.verdict for o in dates if o.finding is not None and o.superseded_by is None]
    all_verdicts = ([r.verdict for r in line_reports] + [f.finding.verdict for f in application] + date_verdicts
                    + ([fund.verdict] if fund.verdict else []))
    overall = _worst(all_verdicts)
    blocked_by: list[str] = []
    for report in line_reports:
        for f in report.findings:
            if f.finding.verdict is Verdict.RED:
                blocked_by.append(f"Line {report.line} ({report.item or report.vendor}): {ruleset.get(f.finding.rule_id).title}")
    for f in application:
        if f.finding.verdict is Verdict.RED:
            blocked_by.append(f"Application: {ruleset.get(f.finding.rule_id).title}")
    for o in dates:
        if o.finding is not None and o.finding.verdict is Verdict.RED and o.superseded_by is None:
            blocked_by.append(f"Dates: {o.title}")
    blocked_by.extend(f"Dates: {block}" for block in hard_blocks)
    blocked_by = list(dict.fromkeys(blocked_by))

    counts = {v.value: 0 for v in Verdict}
    for report in line_reports:
        counts[report.verdict.value] += 1
    totals = MoneyTotals(
        total_cents=total, food_total_cents=food_total, food_per_person_cents=food_pp, food_per_person_text=food_pp_text,
        venue_personnel_cents=vp_total, usg_year_total_cents=year_total,
        ineligible_cents=sum(e.line.amount_cents for e in entries
                             if any(f.finding.verdict is Verdict.RED and ruleset.get(f.finding.rule_id).kind == "ineligible"
                                    for f in e.findings)),
    )
    return MoneyReport(
        as_of=as_of, verdict=overall, verdict_label=VERDICT_LABELS[overall], lines=line_reports, application=application,
        application_passed=app_passed, dates=dates, fund=fund, totals=totals, documents=request.documents, counts=counts,
        draft_allowed=not blocked_by, draft_blocked_by=blocked_by, questions=list(dict.fromkeys(questions)),
        notice=PRECHECK_NOTICE,
    )
