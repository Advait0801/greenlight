"""The year planner: the club's money and events -> calendar, budget, funding strategy, problems and "this week".

Pure Python. It never imports the AI client (tests/unit/test_architecture.py) and duplicates no rule logic:
- every event's obligations, dates, blocked periods, ineligible events and passed deadlines come from the event
  packet's engine (app.services.rule_engine.build_packet), which uses the deadline calculator;
- the fund for each event comes from the money check's fund matching (app.services.money_check.match_fund), and
  money is formatted and caps are read from rule params with the money check's helpers;
- USG's deadline table is only read (app.services.usg_deadline_table), never computed, and shown unconfirmed.
What is new here is what only a whole plan has: sums across events, the per-semester and yearly caps across
events, two funded events on one day, the order to apply in, how the club's money is split, and crowded weeks.
Every problem that rests on a rule is built with app.rules.finding_for, so it carries the rule text and source and
can never be a green or a certain red the rule cannot support.

Everything is recomputed from the request on every call; nothing is stored, so nothing can go stale.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

from app.rules import AcademicCalendar, RuleSet, citation_for, finding_for
from app.rules.calendar import Term
from app.schemas.common import PRECHECK_NOTICE, VERDICT_LABELS, Citation, Finding, Verdict
from app.schemas.events import STATUS_LABELS, EventFacts, EventPacket, PacketObligation
from app.schemas.plans import (
    BudgetSummary,
    CalendarItem,
    CrowdedWeek,
    EventBudget,
    FundingStep,
    FundingStrategy,
    NotPlanned,
    PlanEvent,
    PlanEventResult,
    PlanProblem,
    ProblemType,
    TableDeadline,
    YearPlanReport,
    YearPlanRequest,
)
from app.services import deadlines, usg_deadline_table
from app.schemas.money import BudgetEvent, BudgetLine, MoneyCheckRequest
from app.services.money_check import ORDER, check_budget, limit_cents, match_fund, money
from app.services.rule_engine import build_packet

YEARLY_CAP_RULE = "usg-yearly-cap"
SEMESTER_CAP_RULE = "usg-events-per-semester-cap"
SAME_DAY_RULE = "usg-denial-same-day-events"
TABLE_RULE = usg_deadline_table.DEFINITION_RULE
USG_ATTRIBUTE = "usg_funding"
# A week with at least this many dated items (deadlines, contact-by dates, USG table dates) is highlighted.
CROWDED_WEEK_ITEMS = 5
THIS_WEEK_ITEMS = 3
WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def _fmt(day: date) -> str:
    return f"{WEEKDAYS[day.weekday()]}, {day:%B} {day.day}, {day.year}"


def _short(day: date) -> str:
    return f"{day:%B} {day.day}, {day.year}"


def _worst(verdicts: Iterable[Verdict]) -> Verdict:
    return max(verdicts, key=ORDER.__getitem__, default=Verdict.GREEN)


def _finding(ruleset: RuleSet, rule_id: str, verdict: Verdict, message: str, fix: str | None) -> Finding:
    """A finding from the rule table; a rule that cannot carry this verdict is shown yellow, never upgraded."""
    try:
        return finding_for(ruleset, rule_id, verdict, message, fix)
    except ValueError:
        return finding_for(ruleset, rule_id, Verdict.YELLOW, message, fix)


def _academic_year(day: date, calendar: AcademicCalendar) -> str:
    """USC's academic year runs from the fall term to the end of the summer session. A date inside a term belongs to
    that term's year (Summer Session 2027, May 19 to August 10, is 2026-27); a date between terms belongs to the year
    of the next term to start (winter recess belongs with the spring). Outside the calendar: from August on, the year
    that starts that fall."""
    term = calendar.term_for(day) or next((t for t in calendar.terms if t.classes_begin > day and
                                           (t.classes_begin - day).days < 120), None)
    if term is not None:
        start = term.classes_begin
        first = start.year if start.month >= 8 else start.year - 1
    else:
        first = day.year if day.month >= 8 else day.year - 1
    return f"{first}-{(first + 1) % 100:02d}"


def _where(day: date, calendar: AcademicCalendar) -> str:
    for term in calendar.terms:
        for item in term.breaks:
            if day in item:
                return item.name.lower()
    for recess in calendar.recesses:
        if day in recess:
            return recess.name.lower()
    term = calendar.term_for(day)
    if term is not None:
        return term.name
    return "a date outside Greenlight's calendar"


def _days(event: PlanEvent) -> list[date]:
    if event.event_date is None:
        return []
    last = event.end_date or event.event_date
    return [event.event_date + timedelta(days=i) for i in range((last - event.event_date).days + 1)]


def _facts(event: PlanEvent) -> EventFacts:
    attributes = list(dict.fromkeys(event.attributes))
    if event.usg_request_cents > 0 and USG_ATTRIBUTE not in attributes:
        attributes.append(USG_ATTRIBUTE)
    if (event.end_date is not None and event.event_date is not None and event.end_date > event.event_date
            and "multi_day" not in attributes):
        attributes.append("multi_day")
    possible = [name for name in dict.fromkeys(event.possible_attributes) if name not in attributes]
    return EventFacts(name=event.name, event_date=event.event_date, end_date=event.end_date, venue=event.venue,
                      headcount=event.headcount, attributes=attributes, possible_attributes=possible)


def _usg_reviews(event: PlanEvent, packet: EventPacket, ruleset: RuleSet, calendar: AcademicCalendar,
                 as_of: date) -> list[PacketObligation]:
    """USG's case-by-case reviews (expenses over $4,000, multi-day events) for an event that asks USG for money. They
    come from the money check itself, run on the plan's rough cost as one line; only its 'office decides' findings
    about the application are kept (the line-level findings need real quotes, which the money check asks for)."""
    if event.usg_request_cents == 0:
        return []
    facts = packet.event
    budget_event = BudgetEvent(
        name=event.name, event_date=event.event_date, end_date=event.end_date, expected_attendance=event.headcount,
        venue=event.venue, ticketed=True if "ticket_sales" in facts.attributes else None,
        attributes=[a for a in facts.attributes if a in ruleset.vocabulary.get("event_attributes", {})
                    and not a.startswith("venue_") and a != "ticket_sales"])
    line = BudgetLine(line=1, item="Rough cost from the year plan", quantity=1,
                      unit_price_cents=event.estimated_cost_cents, amount_cents=event.estimated_cost_cents)
    report = check_budget(MoneyCheckRequest(event=budget_event, lines=[line]), ruleset, calendar, as_of)
    out: list[PacketObligation] = []
    for item in report.application:
        f = item.finding
        rule = ruleset.get(f.rule_id)
        if f.verdict is not Verdict.OFFICE_DECIDES:
            continue
        out.append(PacketObligation(
            rule_id=rule.id, title=rule.title, owner_office=rule.owner_office, status="office_decides",
            status_label=STATUS_LABELS["office_decides"], due=None, due_note=None, violated=False, past_due=False,
            message=rule.message, note=f"From the money check on the plan's rough cost: {f.message}", fix=f.fix, finding=f,
            citation=f.citation, link=rule.source_url, triggered_by=[USG_ATTRIBUTE], from_possible_attribute=False))
    return out


def _active(packet: EventPacket) -> list[PacketObligation]:
    return [o for o in packet.obligations if o.superseded_by is None]


@dataclass
class _Event:
    plan: PlanEvent
    packet: EventPacket
    term: Term | None
    usg_deadlines: list[TableDeadline]

    @property
    def asks_usg(self) -> bool:
        return self.plan.usg_request_cents > 0


class _Problems:
    """Problems grouped by (type, rule): one problem lists every event it concerns."""

    def __init__(self, ruleset: RuleSet) -> None:
        self.ruleset = ruleset
        self.items: list[PlanProblem] = []
        self._index: dict[tuple[str, str | None, str], int] = {}

    def add(self, kind: ProblemType, rule_id: str | None, verdict: Verdict, events: list[str], note: str,
            fix: str | None = None, *, group: str = "", also: Iterable[str] = ()) -> None:
        key = (kind, rule_id, group)
        if key in self._index:
            existing = self.items[self._index[key]]
            merged = list(dict.fromkeys([*existing.events, *events]))
            notes = existing.note if note in existing.note else f"{existing.note} {note}"
            update: dict[str, object] = {"events": merged, "note": notes}
            if ORDER[verdict] > ORDER[existing.severity] and rule_id is not None:
                finding = _finding(self.ruleset, rule_id, verdict, notes, existing.fix or fix)
                update.update(severity=finding.verdict, severity_label=VERDICT_LABELS[finding.verdict], finding=finding)
            elif ORDER[verdict] > ORDER[existing.severity]:
                update.update(severity=verdict, severity_label=VERDICT_LABELS[verdict])
            elif existing.finding is not None:
                update["finding"] = existing.finding.model_copy(update={"message": notes})
            self.items[self._index[key]] = existing.model_copy(update=update)
            return
        finding = _finding(self.ruleset, rule_id, verdict, note, fix) if rule_id else None
        shown = finding.verdict if finding else verdict
        self._index[key] = len(self.items)
        self.items.append(PlanProblem(
            type=kind, rule_id=rule_id, severity=shown, severity_label=VERDICT_LABELS[shown], events=list(dict.fromkeys(events)),
            note=note, fix=fix, citation=citation_for(self.ruleset, rule_id) if rule_id else None, finding=finding,
            also_cites=[citation_for(self.ruleset, r) for r in also],
        ))


# ---------------------------------------------------------------------------------------------------------------
# USG deadlines from the table


def _usg_deadlines(ruleset: RuleSet, calendar: AcademicCalendar, sources_dir: Path, event: PlanEvent,
                   packet: EventPacket, as_of: date) -> list[TableDeadline]:
    """For each USG deadline the packet applies that USG's table has a column for (rule params
    deadline_table_column): the latest date it can fall on, and what the unconfirmed table copy says."""
    start = event.event_date
    if start is None or event.usg_request_cents == 0:
        return []
    term = calendar.term_for(start)
    out: list[TableDeadline] = []
    for o in _active(packet):
        rule = ruleset.get(o.rule_id)
        column = rule.params.get("deadline_table_column")
        if column not in usg_deadline_table.COLUMNS or rule.offset is None or o.from_possible_attribute:
            continue
        latest = deadlines.shift(start, rule.offset, "weeks", "before")
        if latest is None:
            continue
        found = usg_deadline_table.lookup(ruleset, sources_dir, start, column)
        table_day = found.deadline
        before = term is not None and (latest < term.classes_begin or (table_day is not None and table_day < term.classes_begin))
        out.append(TableDeadline(
            rule_id=rule.id, title=rule.title, column=column, weeks=rule.offset, latest_possible=latest,
            latest_possible_in=_where(latest, calendar), table_status=found.status, table_date=table_day,
            table_row_to_confirm=found.to_confirm, before_semester=before,
            passed_per_table=table_day is not None and table_day < as_of,
            citation=citation_for(ruleset, rule.id), table_citation=citation_for(ruleset, TABLE_RULE),
        ))
    return out


def _table_text(d: TableDeadline) -> str:
    if d.table_status == "date" and d.table_date is not None:
        return (f"Greenlight's copy of USG's deadline table (transcribed by hand, not yet confirmed) gives "
                f"{_fmt(d.table_date)}")
    if d.table_status == "no_deadline":
        return "Greenlight's copy of USG's deadline table (not yet confirmed) lists no deadline for that week"
    if d.table_status == "not_applicable":
        return "Greenlight's copy of USG's deadline table (not yet confirmed) marks that week N/A"
    return "Greenlight's copy of USG's deadline table (not yet confirmed) has no row for that week"


# ---------------------------------------------------------------------------------------------------------------
# The plan


def plan_year(request: YearPlanRequest, ruleset: RuleSet, calendar: AcademicCalendar, as_of: date,
              sources_dir: Path) -> YearPlanReport:
    problems = _Problems(ruleset)
    questions: list[str] = []

    events: list[_Event] = []
    for plan_event in request.events:
        packet = build_packet(_facts(plan_event), ruleset, calendar, as_of)
        reviews = _usg_reviews(plan_event, packet, ruleset, calendar, as_of)
        if reviews:
            packet = packet.model_copy(update={
                "obligations": [*packet.obligations, *reviews],
                "counts": {**packet.counts, "office_decides": packet.counts.get("office_decides", 0) + len(reviews)}})
        term = calendar.term_for(plan_event.event_date) if plan_event.event_date else None
        events.append(_Event(plan=plan_event, packet=packet, term=term,
                             usg_deadlines=_usg_deadlines(ruleset, calendar, sources_dir, plan_event, packet, as_of)))
        for question in packet.questions:
            questions.append(f"{plan_event.name}: {question}")

    _packet_problems(events, problems, ruleset)
    _input_problems(request, events, problems, calendar)
    _deadline_problems(events, problems)
    _same_day_problems(events, problems, ruleset)
    semester_cap = _semester_problems(events, problems, ruleset)
    yearly_cap = limit_cents(ruleset.get(YEARLY_CAP_RULE), "max_usd_per_year")
    _yearly_problems(request, events, problems, ruleset, yearly_cap, as_of, calendar)
    if request.usg_received_this_year_cents is None and any(e.asks_usg for e in events):
        questions.append("How much has the club already received from USG this academic year?")
    if request.level == "graduate" and any(e.asks_usg for e in events):
        questions.append("Greenlight checks the Undergraduate Student Government (USG) funding rules. Is this an "
                         "undergraduate club? Graduate clubs apply to the Graduate Student Government instead.")

    strategy = _strategy(request, events, problems, ruleset, semester_cap, yearly_cap, as_of, calendar)
    budget = _budget(request, events, strategy, ruleset, yearly_cap, as_of, calendar)
    by_key = {row.key: row for row in budget.rows}

    calendar_items = _calendar(events, ruleset)
    crowded = _crowded(calendar_items)
    planned_keys = {step.key for step in strategy.steps}
    upcoming = [item for item in calendar_items if item.kind != "event" and item.day >= as_of and not item.past_due
                and not (item.event_key not in planned_keys and item.rule_id is not None
                         and ruleset.get(item.rule_id).domain == "funding")]
    this_week = upcoming[:THIS_WEEK_ITEMS]

    problem_verdicts: dict[str, list[Verdict]] = defaultdict(list)
    for p in problems.items:
        for key in p.events:
            problem_verdicts[key].append(p.severity)
    results: list[PlanEventResult] = []
    for e in events:
        packet_verdicts = [o.finding.verdict for o in _active(e.packet) if o.finding is not None]
        verdict = _worst([*packet_verdicts, *problem_verdicts[e.plan.key]])
        results.append(PlanEventResult(
            key=e.plan.key, name=e.plan.name, event_date=e.plan.event_date, end_date=e.plan.end_date,
            term=e.term.id if e.term else None, asks_usg=e.asks_usg, verdict=verdict, verdict_label=VERDICT_LABELS[verdict],
            packet=e.packet, usg_deadlines=e.usg_deadlines, budget=by_key[e.plan.key]))

    ordered = sorted(problems.items, key=lambda p: (-ORDER[p.severity], p.type, p.events))
    counts = {v.value: sum(1 for p in ordered if p.severity is v) for v in Verdict}
    return YearPlanReport(
        as_of=as_of, club_name=request.club_name, events=results, calendar=calendar_items, crowded_weeks=crowded,
        budget=budget, strategy=strategy, problems=ordered, this_week=this_week,
        questions=list(dict.fromkeys(questions)), counts=counts, notice=PRECHECK_NOTICE)


def _packet_problems(events: list[_Event], problems: _Problems, ruleset: RuleSet) -> None:
    """Blocked items and passed deadlines, exactly as each event's packet shows them."""
    for e in events:
        key = e.plan.key
        for o in _active(e.packet):
            rule = ruleset.get(o.rule_id)
            verdict = o.finding.verdict if o.finding is not None else Verdict.YELLOW
            if o.status == "blocked":
                kind: ProblemType
                if rule.domain == "funding" and rule.kind == "ineligible":
                    kind = "not_fundable_as_described"
                elif rule.kind == "blocked_period":
                    kind = "event_in_blocked_period"
                elif rule.kind == "banned":
                    kind = "banned_money_source" if rule.domain == "outside_money" else "banned_at_event"
                else:
                    kind = "blocked_as_described"
                note = f"{e.plan.name}: {o.note or o.message}"
                problems.add(kind, rule.id, verdict, [key], note, o.fix)
            elif o.past_due:
                when = f"was due on {_fmt(o.due)}" if o.due is not None else "has already passed"
                note = f"{e.plan.name}: {o.title} {when}." + (f" {o.note}" if o.note and o.due is None else "")
                fix = next((f.text for f in o.fallbacks), None) or next((f.text for f in e.packet.fallbacks), None)
                problems.add("deadline_passed", rule.id, verdict, [key], note, fix)
        if e.plan.event_date is not None and e.plan.event_date < e.packet.as_of:
            problems.add("event_date_passed", None, Verdict.RED, [key],
                         f"{e.plan.name}: the date, {_fmt(e.plan.event_date)}, has already passed.",
                         "Change the date or remove the event from the plan.", group=key)


def _input_problems(request: YearPlanRequest, events: list[_Event], problems: _Problems, calendar: AcademicCalendar) -> None:
    unavailable = set(request.unavailable_dates)
    for e in events:
        key = e.plan.key
        if e.plan.event_date is None:
            problems.add("event_needs_date", None, Verdict.YELLOW, [key],
                         f"{e.plan.name} has no date yet, so none of its deadlines can be dated.",
                         "Give the event a date, even a rough one.")
            continue
        clash = sorted(day for day in _days(e.plan) if day in unavailable)
        if clash:
            problems.add("officers_unavailable", None, Verdict.YELLOW, [key],
                         f"{e.plan.name} is on {', '.join(_short(d) for d in clash)}, which you marked as a date the officers are unavailable.",
                         "Move the event or find officers who can run it.", group=key)
        if not all(calendar.covers(day) for day in _days(e.plan)):
            problems.add("outside_calendar", None, Verdict.YELLOW, [key],
                         f"{e.plan.name} falls outside the academic calendar Greenlight has (2026-27), so holidays, breaks and "
                         "USG dates could not be checked for it.", "Check the dates with each office.")


def _deadline_problems(events: list[_Event], problems: _Problems) -> None:
    for e in events:
        for d in e.usg_deadlines:
            if d.before_semester:
                note = (f"{e.plan.name}: counted back {d.weeks} calendar weeks from {_short(e.plan.event_date or d.latest_possible)}, "
                        f"{d.title} falls on {_short(d.latest_possible)} at the latest ({d.latest_possible_in}). "
                        f"{_table_text(d)}. Either way it falls before the semester of the event.")
                problems.add("deadline_in_previous_semester_or_break", d.rule_id, Verdict.YELLOW, [e.plan.key], note,
                             "Apply to USG before the semester ends; confirm the date in USG's deadline table or with "
                             "usgfunds@usc.edu.", also=[TABLE_RULE])
            if d.passed_per_table and d.table_date is not None:
                note = f"{e.plan.name}: {d.title}: {_table_text(d)}, which has passed."
                problems.add("usg_deadline_passed_per_table", d.rule_id, Verdict.YELLOW, [e.plan.key], note,
                             "Confirm with USG (usgfunds@usc.edu); if the deadline has passed, plan the event without USG "
                             "money or move it later.", also=[TABLE_RULE])
            elif d.table_status in ("no_deadline", "not_applicable"):
                note = f"{e.plan.name}: {d.title}: {_table_text(d)}, so USG may not fund the event that week."
                problems.add("usg_no_deadline_in_table", d.rule_id, Verdict.YELLOW, [e.plan.key], note,
                             "Confirm with USG (usgfunds@usc.edu) or move the event.", also=[TABLE_RULE])


def _same_day_problems(events: list[_Event], problems: _Problems, ruleset: RuleSet) -> None:
    by_day: dict[date, list[str]] = defaultdict(list)
    names = {e.plan.key: e.plan.name for e in events}
    for e in events:
        if e.asks_usg:
            for day in _days(e.plan):
                by_day[day].append(e.plan.key)
    seen: set[frozenset[str]] = set()
    fix_template = ruleset.get(SAME_DAY_RULE).fix_template or ""
    for day in sorted(by_day):
        keys = by_day[day]
        if len(keys) < 2 or frozenset(keys) in seen:
            continue
        seen.add(frozenset(keys))
        listed = ", ".join(names[k] for k in keys)
        problems.add("same_day_funding_requests", SAME_DAY_RULE, Verdict.YELLOW, keys,
                     f"{len(keys)} events asking USG for money on {_short(day)}: {listed}.",
                     fix_template.replace("{date}", _short(day)), group=",".join(sorted(keys)))


def _semester_problems(events: list[_Event], problems: _Problems, ruleset: RuleSet) -> int:
    rule = ruleset.get(SEMESTER_CAP_RULE)
    cap = int(rule.params["max_funded_events_per_semester"])
    by_term: dict[str, list[_Event]] = defaultdict(list)
    for e in events:
        if e.asks_usg and e.term is not None:
            by_term[e.term.id].append(e)
    for term_id, group in by_term.items():
        if len(group) > cap:
            term_name = group[0].term.name if group[0].term else term_id
            problems.add("funded_events_over_semester_cap", rule.id, Verdict.YELLOW, [e.plan.key for e in group],
                         f"{len(group)} events in {term_name} ask USG for money; USG's web page says up to {cap} funded events "
                         "a semester (not in the guidelines, so confirm with USG).",
                         rule.fix_template, group=term_id)
    return cap


def _yearly_problems(request: YearPlanRequest, events: list[_Event], problems: _Problems, ruleset: RuleSet,
                     cap: int, as_of: date, calendar: AcademicCalendar) -> None:
    rule = ruleset.get(YEARLY_CAP_RULE)
    by_year: dict[str, list[_Event]] = defaultdict(list)
    for e in events:
        if e.asks_usg:
            by_year[_academic_year(e.plan.event_date or as_of, calendar)].append(e)
    this_year = _academic_year(as_of, calendar)
    for year, group in sorted(by_year.items()):
        requested = sum(e.plan.usg_request_cents for e in group)
        keys = [e.plan.key for e in group]
        if year == this_year:
            if request.usg_received_this_year_cents is None:
                problems.add("yearly_cap_unknown", rule.id, Verdict.YELLOW, keys,
                             f"Greenlight does not know how much the club has received from USG in {year}, so it cannot "
                             f"check the {money(cap)} yearly cap (requests in the plan: {money(requested)}).",
                             "Enter the amount received this year.", group=year)
                continue
            received = request.usg_received_this_year_cents
        else:
            received = 0
        total = received + requested
        if total > cap:
            over = total - cap
            if received:
                note = (f"{year}: already received {money(received)}; requests of {money(requested)} make {money(total)}, "
                        f"over the {money(cap)} yearly cap by {money(over)}.")
            else:
                note = f"{year}: USG requests total {money(requested)}, over the {money(cap)} yearly cap by {money(over)}."
            if year != this_year:
                note += " Greenlight assumes nothing is received yet that year."
            problems.add("over_yearly_cap", rule.id, Verdict.RED, keys, note,
                         f"Ask USG for {money(over)} less across these events, or fund that much another way.", group=year)


# ---------------------------------------------------------------------------------------------------------------
# Funding strategy


def _apply_by(e: _Event) -> TableDeadline | None:
    """The earliest dated deadline in the table copy, or else the earliest latest-possible date."""
    if not e.usg_deadlines:
        return None
    return min(e.usg_deadlines, key=lambda d: (d.table_date or d.latest_possible, d.rule_id))


def _not_fundable(e: _Event, ruleset: RuleSet) -> tuple[str, Verdict, Citation | None] | None:
    if e.plan.event_date is None:
        return "No date yet, so its USG deadlines cannot be worked out.", Verdict.YELLOW, None
    if e.plan.event_date < e.packet.as_of:
        return "The event date has passed.", Verdict.RED, None
    for o in _active(e.packet):
        rule = ruleset.get(o.rule_id)
        if rule.domain != "funding":
            continue
        verdict = o.finding.verdict if o.finding is not None else Verdict.YELLOW
        if o.status == "blocked":
            return f"{o.title}: {o.note or o.message}", verdict, o.citation
        if o.past_due:
            return f"{o.title}: the deadline has passed.", verdict, o.citation
        if o.violated or (rule.kind == "ineligible" and o.from_possible_attribute):
            # Possibly against a funding rule (for example tickets may be sold, or a summer date): not planned as
            # certain money until a person confirms.
            return f"{o.title}: {o.note or o.message} Confirm before counting on USG money.", Verdict.YELLOW, o.citation
    if e.term is None:
        return "The event is outside the academic terms in Greenlight's calendar.", Verdict.YELLOW, None
    for d in e.usg_deadlines:
        if d.passed_per_table and d.table_date is not None:
            return (f"{d.title}: {_table_text(d)}, which has passed. Confirm with USG.", Verdict.YELLOW,
                    d.table_citation)
        if d.table_status in ("no_deadline", "not_applicable", "not_in_table"):
            return f"{_table_text(d)}. Confirm with USG.", Verdict.YELLOW, d.table_citation
    return None


def _strategy(request: YearPlanRequest, events: list[_Event], problems: _Problems, ruleset: RuleSet, semester_cap: int,
              yearly_cap: int, as_of: date, calendar: AcademicCalendar) -> FundingStrategy:
    sem_rule, year_rule = ruleset.get(SEMESTER_CAP_RULE), ruleset.get(YEARLY_CAP_RULE)
    not_planned: list[NotPlanned] = []
    fundable: list[_Event] = []
    for e in events:
        if not e.asks_usg:
            continue
        reason = _not_fundable(e, ruleset)
        if reason is not None:
            text, verdict, citation = reason
            not_planned.append(NotPlanned(key=e.plan.key, name=e.plan.name, requested_cents=e.plan.usg_request_cents,
                                          reason=text, severity=verdict, citation=citation))
        else:
            fundable.append(e)

    # Largest requests first (funding is first come, first served and a fund can close early), then by date.
    def priority(e: _Event) -> tuple[int, date, str]:
        return (-e.plan.usg_request_cents, e.plan.event_date or date.max, e.plan.key)

    chosen: list[_Event] = []
    per_term: dict[str, int] = defaultdict(int)
    for e in sorted(fundable, key=priority):
        term_id = e.term.id if e.term else ""
        if per_term[term_id] >= semester_cap:
            not_planned.append(NotPlanned(
                key=e.plan.key, name=e.plan.name, requested_cents=e.plan.usg_request_cents,
                reason=(f"Would be funded event number {per_term[term_id] + 1} in {e.term.name if e.term else 'the term'}; "
                        f"USG's web page says up to {semester_cap} a semester. Not planned; confirm the limit with USG."),
                severity=Verdict.YELLOW, citation=citation_for(ruleset, sem_rule.id)))
            continue
        per_term[term_id] += 1
        chosen.append(e)

    this_year = _academic_year(as_of, calendar)
    remaining: dict[str, int] = {}
    unknown_years: set[str] = set()
    steps: list[FundingStep] = []
    for e in chosen:
        year = _academic_year(e.plan.event_date or as_of, calendar)
        if year not in remaining:
            received = request.usg_received_this_year_cents if year == this_year else 0
            if received is None:
                # Not known: the club cannot have received less than nothing, so the cap still limits the plan.
                unknown_years.add(year)
                received = 0
            remaining[year] = max(yearly_cap - received, 0)
        left = remaining[year]
        requested = e.plan.usg_request_cents
        if left <= 0:
            used_by = ("by the larger requests above" if year in unknown_years or year != this_year
                       or not request.usg_received_this_year_cents else
                       "by the money already received and the larger requests above")
            not_planned.append(NotPlanned(
                key=e.plan.key, name=e.plan.name, requested_cents=requested,
                reason=f"The {money(yearly_cap)} yearly cap for {year} is used up {used_by}.",
                severity=Verdict.RED, citation=citation_for(ruleset, year_rule.id)))
            continue
        planned = min(requested, left)
        remaining[year] = left - planned
        note = ("Within the yearly cap." if planned == requested else
                f"Only {money(planned)} of the {money(requested)} fits under the {money(yearly_cap)} yearly cap for {year}.")
        if year in unknown_years:
            note += (f" The amount already received from USG in {year} is not known, so Greenlight assumed none; "
                     "enter it, because anything received lowers what fits.")
        steps.append(FundingStep(
            order=len(steps) + 1, key=e.plan.key, name=e.plan.name, term=e.term.id if e.term else None,
            requested_cents=requested, planned_cents=planned, status="apply" if planned == requested else "apply_partly",
            fund=match_fund(ruleset, e.plan.fund, None), apply_by=_apply_by(e), note=note))
    explanation = [
        "Events USG cannot fund as described, or whose USG deadline has passed, are left out.",
        f"At most {semester_cap} events a semester are planned (USG's web page; not in the guidelines, so confirm with USG).",
        f"The largest requests are planned first, up to the {money(yearly_cap)} yearly cap: USG funds applications first "
        "come, first served, and a fund can close early. Apply for these as early as you can.",
        "USG decides every application. This is a plan, not a promise of money.",
    ]
    return FundingStrategy(steps=steps, not_planned=not_planned, semester_cap=semester_cap, yearly_cap_cents=yearly_cap,
                           explanation=explanation,
                           citations=[citation_for(ruleset, sem_rule.id), citation_for(ruleset, year_rule.id)])


# ---------------------------------------------------------------------------------------------------------------
# Budget


def _budget(request: YearPlanRequest, events: list[_Event], strategy: FundingStrategy, ruleset: RuleSet,
            yearly_cap: int, as_of: date, calendar: AcademicCalendar) -> BudgetSummary:
    planned = {step.key: step.planned_cents for step in strategy.steps}
    available = request.money_on_hand_cents + request.expected_income_cents
    remaining = available
    rows: dict[str, EventBudget] = {}
    # The club's own money goes to events in date order: earlier events need it first. Undated events come last.
    for e in sorted(events, key=lambda e: (e.plan.event_date or date.max, e.plan.key)):
        cost = e.plan.estimated_cost_cents
        usg = planned.get(e.plan.key, 0)
        need = cost - usg
        club = min(need, remaining)
        remaining -= club
        rows[e.plan.key] = EventBudget(key=e.plan.key, name=e.plan.name, cost_cents=cost,
                                       usg_requested_cents=e.plan.usg_request_cents, usg_planned_cents=usg,
                                       club_money_cents=club, shortfall_cents=need - club)
    ordered = [rows[e.plan.key] for e in events]
    total = sum(r.cost_cents for r in ordered)
    requested = sum(r.usg_requested_cents for r in ordered)
    # Over the yearly cap, academic year by year (money received is known only for the current year).
    this_year = _academic_year(as_of, calendar)
    by_year: dict[str, int] = defaultdict(int)
    for e in events:
        if e.asks_usg:
            by_year[_academic_year(e.plan.event_date or as_of, calendar)] += e.plan.usg_request_cents
    over: int | None = 0
    for year, amount in by_year.items():
        received = request.usg_received_this_year_cents if year == this_year else 0
        if received is None:
            over = None
            break
        over = (over or 0) + max(received + amount - yearly_cap, 0)
    usg_planned = sum(r.usg_planned_cents for r in ordered)
    club_money = sum(r.club_money_cents for r in ordered)
    shortfall = sum(r.shortfall_cents for r in ordered)
    explanation = [
        f"The club has {money(available)}: {money(request.money_on_hand_cents)} on hand and "
        f"{money(request.expected_income_cents)} expected.",
        f"The events cost {money(total)} in all. Planned USG money ({money(usg_planned)}) is counted first, only for events "
        "in the funding plan; the club's money then goes to events in date order.",
        f"Still to find: {money(shortfall)}." if shortfall else "Every event is covered on paper.",
    ]
    return BudgetSummary(
        total_cost_cents=total, funds_available_cents=available, gap_before_usg_cents=max(total - available, 0),
        usg_requested_cents=requested, usg_requested_over_yearly_cap_cents=over, yearly_cap_cents=yearly_cap,
        usg_planned_cents=usg_planned, club_money_cents=club_money, shortfall_cents=shortfall,
        unallocated_cents=available - club_money, rows=ordered, explanation=explanation,
        citation=citation_for(ruleset, YEARLY_CAP_RULE))


# ---------------------------------------------------------------------------------------------------------------
# Calendar


def _calendar(events: list[_Event], ruleset: RuleSet) -> list[CalendarItem]:
    items: list[CalendarItem] = []
    for e in events:
        name, key = e.plan.name, e.plan.key
        if e.plan.event_date is not None:
            items.append(CalendarItem(day=e.plan.event_date, kind="event", event_key=key, event_name=name, rule_id=None,
                                      title=name if e.plan.end_date is None else f"{name} (until {_short(e.plan.end_date)})",
                                      status=None, status_label="The event", past_due=False, unconfirmed=False, citation=None))
        for o in _active(e.packet):
            if o.due is not None:
                items.append(CalendarItem(day=o.due, kind="due", event_key=key, event_name=name, rule_id=o.rule_id,
                                          title=o.title, status=o.status, status_label=STATUS_LABELS[o.status],
                                          past_due=o.past_due, unconfirmed=False, citation=o.citation))
            elif o.contact_by is not None:
                items.append(CalendarItem(day=o.contact_by, kind="contact_by", event_key=key, event_name=name,
                                          rule_id=o.rule_id, title=f"Contact the office: {o.title}", status=o.status,
                                          status_label=STATUS_LABELS[o.status], past_due=o.contact_by < e.packet.as_of,
                                          unconfirmed=False, citation=o.citation))
        for d in e.usg_deadlines:
            if d.table_date is not None:
                items.append(CalendarItem(day=d.table_date, kind="usg_table", event_key=key, event_name=name,
                                          rule_id=d.rule_id, title=f"Apply to USG: {d.title}", status="check_with_office",
                                          status_label="Check with USG: date from an unconfirmed copy of USG's table",
                                          past_due=d.passed_per_table, unconfirmed=True, citation=d.table_citation))
    kind_order = {"usg_table": 0, "due": 1, "contact_by": 2, "event": 3}
    return sorted(items, key=lambda i: (i.day, kind_order[i.kind], i.event_key, i.rule_id or ""))


def _crowded(items: list[CalendarItem]) -> list[CrowdedWeek]:
    weeks: dict[date, list[CalendarItem]] = defaultdict(list)
    for item in items:
        if item.kind != "event":
            weeks[item.day - timedelta(days=item.day.weekday())].append(item)
    out = []
    for monday, group in sorted(weeks.items()):
        if len(group) >= CROWDED_WEEK_ITEMS:
            out.append(CrowdedWeek(week_start=monday, week_end=monday + timedelta(days=6), count=len(group),
                                   events=list(dict.fromkeys(i.event_key for i in group))))
    return out
