"""The rule engine for events: event facts + rule table + academic calendar -> the event packet.

Pure Python. It never imports the AI client (tests/unit/test_architecture.py). Every date comes from
app.services.deadlines; every verdict follows from the rule table (certainty, severity, kind) and the facts.

Which rules apply (data/eval/README.md, "Event obligations: scope and status"): rules in events.json and
outside_money.json of kind deadline, requirement, cap, banned or blocked_period whose triggers match the
event's venue and attributes; and, when the event asks for USG funding, funding.json rules of kind deadline,
blocked_period or ineligible whose triggers match.
"""

from __future__ import annotations

from collections.abc import Iterable
from datetime import date, timedelta

from app.rules import AcademicCalendar, RuleSet, citation_for, finding_for
from app.rules.schema import Rule
from app.schemas.common import PRECHECK_NOTICE, Finding, Verdict
from app.schemas.events import (
    STATUS_LABELS,
    EventFacts,
    EventPacket,
    Fallback,
    PacketObligation,
    SourceConflict,
    Status,
    TimelineEntry,
)
from app.services import deadlines

EVENT_KINDS = {"deadline", "requirement", "cap", "banned", "blocked_period"}
FUNDING_KINDS = {"deadline", "blocked_period", "ineligible"}
VENUE_GROUP = "event_attributes"
ALLOWED_GROUPS = ("event_attributes", "facts", "application_facts")
# Checks the engine decides from the event's dates alone. When they pass on a certain rule, the item is green.
DATE_CHECKED = {
    "tes-no-events-first-three-weeks",
    "social-events-not-study-days-finals",
    "alcohol-thursday-saturday",
    "usg-no-funding-breaks",
    "usg-faq-no-summer-funding",
    "tabling-blocked-days",
    "tabling-hours",
    "classroom-requests-week-4",
}
WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


class UnknownAttribute(ValueError):
    pass


def known_names(ruleset: RuleSet) -> set[str]:
    return {name for group in ALLOWED_GROUPS for name in ruleset.vocabulary.get(group, {})}


def _fmt(day: date) -> str:
    return f"{WEEKDAYS[day.weekday()]}, {day.strftime('%B')} {day.day}, {day.year}"


def _hit(rule: Rule, present: set[str]) -> bool:
    if not rule.triggers:
        return False
    if rule.trigger_mode == "all":
        return all(trigger in present for trigger in rule.triggers)
    return any(trigger in present for trigger in rule.triggers)


def _in_scope(rule: Rule, present: set[str]) -> bool:
    if rule.domain in ("events", "outside_money"):
        return rule.kind in EVENT_KINDS
    if rule.domain == "funding":
        return "usg_funding" in present and rule.kind in FUNDING_KINDS
    return False


def select_rules(ruleset: RuleSet, present: set[str]) -> list[Rule]:
    """Every rule in scope whose triggers match `present` (the venue and the attributes), in table order."""
    return [rule for rule in ruleset if _in_scope(rule, present) and _hit(rule, present)]


def _days(facts: EventFacts) -> list[date]:
    if facts.event_date is None:
        return []
    end = facts.end_date or facts.event_date
    return [facts.event_date + timedelta(days=i) for i in range((end - facts.event_date).days + 1)]


class _DateCheck:
    """The result of a date check: violated True/False, or None when it cannot be decided, with a note."""

    def __init__(self, violated: bool | None, note: str | None = None, *, confirm: bool = False) -> None:
        self.violated = violated
        self.note = note
        self.confirm = confirm  # the date falls where the source is unclear: check with the office


def _date_check(rule: Rule, facts: EventFacts, calendar: AcademicCalendar) -> _DateCheck:
    days = _days(facts)
    if not days:
        return _DateCheck(None, "The date is not known yet, so Greenlight cannot check it against this rule.")
    uses_calendar = rule.id not in ("tes-no-events-first-three-weeks", "alcohol-thursday-saturday", "tabling-hours")
    if uses_calendar and not all(calendar.covers(day) for day in days):
        return _DateCheck(None, f"Greenlight's academic calendar ({calendar.title}) does not cover this date; check it with the office.")

    if rule.id == "tes-no-events-first-three-weeks":
        through = date.fromisoformat(rule.params["no_events_through"])
        window = rule.params.get("confirm_window") or {}
        window_start = date.fromisoformat(window["start"]) if window else None
        window_end = date.fromisoformat(window["end"]) if window else None
        january = date(through.year, 1, 1)
        if any(january <= day <= through for day in days):
            return _DateCheck(True, f"Trojan Event Services: events can start after {_fmt(through)}.")
        if window_start and window_end and any(window_start <= day <= window_end for day in days):
            return _DateCheck(False, f"{window_start.strftime('%B')} {window_start.day} to {window_end.day}: 'the first 3 weeks' could "
                              "run to the end of that week; confirm the date with Trojan Event Services.", confirm=True)
        return _DateCheck(False)
    if rule.id == "social-events-not-study-days-finals":
        hit = [day for day in days if calendar.is_study_day_or_final_exam(day)]
        return _DateCheck(bool(hit), f"{_fmt(hit[0])} falls on study days or final exams." if hit else None)
    if rule.id == "usg-no-funding-breaks":
        hit = [day for day in days if calendar.is_break(day) or calendar.is_university_holiday(day) or calendar.is_study_day_or_final_exam(day)]
        return _DateCheck(bool(hit), f"{_fmt(hit[0])} falls in a university holiday, break, study days or finals." if hit else None)
    if rule.id == "usg-faq-no-summer-funding":
        hit = [day for day in days if (term := calendar.term_for(day)) is None or term.id.startswith("summer")]
        return _DateCheck(bool(hit), f"{_fmt(hit[0])} is outside the fall and spring semesters." if hit else None)
    if rule.id == "alcohol-thursday-saturday":
        allowed = set(rule.params.get("allowed_weekdays") or [])
        hit = [day for day in days if WEEKDAYS[day.weekday()] not in allowed]
        return _DateCheck(bool(hit), f"{_fmt(hit[0])} is not a Thursday, Friday or Saturday." if hit else None)
    if rule.id == "tabling-hours":
        allowed = set(rule.params.get("allowed_days") or [])
        hit = [day for day in days if WEEKDAYS[day.weekday()] not in allowed]
        return _DateCheck(bool(hit), f"{_fmt(hit[0])} is a weekend day." if hit else None)
    if rule.id == "tabling-blocked-days":
        hit = [day for day in days if calendar.is_university_holiday(day)]
        return _DateCheck(bool(hit), f"{_fmt(hit[0])} is a university holiday." if hit else None)
    if rule.id == "classroom-requests-week-4":
        term = calendar.term_for(days[0])
        if term is None:
            return _DateCheck(None, "The date is outside a semester; ask Classroom Scheduling.")
        week = int(rule.params.get("requests_open_week", 4))
        opens = term.classes_begin - timedelta(days=term.classes_begin.weekday()) + timedelta(weeks=week - 1)
        if days[0] < opens:
            return _DateCheck(True, f"Classroom requests open in week {week} ({_fmt(opens)}), after this date.")
        return _DateCheck(False)
    return _DateCheck(None)


def _status(ruleset: RuleSet, rule: Rule, violated: bool | None, *, unsure: bool) -> Status:
    """Status follows from the rule's certainty, severity and kind (data/eval/README.md)."""
    if not ruleset.is_certain(rule.id) or rule.severity == "yellow" or unsure:
        return "check_with_office"
    if rule.severity == "office_decides":
        return "office_decides"
    if violated:
        return "blocked"
    return "to_do" if rule.kind in ("deadline", "requirement") else "condition"


def _finding(ruleset: RuleSet, rule: Rule, status: Status, message: str, fix: str | None, *, green: bool, past_due: bool) -> Finding | None:
    shown = ruleset.display_severity(rule.id)
    if status == "blocked" or (past_due and status == "to_do"):
        verdict = Verdict.RED if shown == "red" else Verdict.YELLOW
    elif status == "check_with_office":
        verdict = Verdict.YELLOW
    elif status == "office_decides":
        verdict = Verdict.OFFICE_DECIDES
    elif green:
        verdict = Verdict.GREEN
    else:
        return None
    try:
        return finding_for(ruleset, rule.id, verdict, message, fix)
    except ValueError:
        # The Finding type refused the verdict (e.g. green on a rule that cannot be a pass): never upgrade.
        return finding_for(ruleset, rule.id, Verdict.YELLOW, message, fix) if verdict is not Verdict.YELLOW else None


def _describe(ruleset: RuleSet, name: str) -> str:
    for group in ALLOWED_GROUPS:
        if name in ruleset.vocabulary.get(group, {}):
            return ruleset.vocabulary[group][name]
    return name


def _fix(rule: Rule) -> str | None:
    if rule.fix_template and "{" not in rule.fix_template:
        return rule.fix_template
    return None


def _lead_time(rule: Rule) -> str:
    unit = (rule.unit or "").replace("_", " ")
    if rule.offset == 1 and unit.endswith("s"):
        unit = unit[:-1]
    return f"{rule.offset} {unit} {rule.direction} the {(rule.anchor or 'event_date').replace('_', ' ')}"


def _due_note(rule: Rule, facts: EventFacts, due: date | None) -> str | None:
    if rule.kind != "deadline":
        return None
    if due is not None:
        return f"{_lead_time(rule)}, counted by Greenlight's deadline calculator."
    if rule.unit == "academic_weeks":
        return (f"{_lead_time(rule)}. No source defines an academic week, so Greenlight gives no date: "
                "check USG's Funding Application Deadlines table or ask usgfunds@usc.edu.")
    if rule.unit == "hours" or (rule.anchor or "event_date") not in ("event_date", "event_end_date"):
        return f"{_lead_time(rule)}. Greenlight cannot date this until that day is known."
    if facts.event_date is None:
        return f"{_lead_time(rule)}. Give the event date to see the due date."
    return f"{_lead_time(rule)}."


def _fallbacks(ruleset: RuleSet, rule: Rule, as_of: date, triggered_by: list[str], facts: EventFacts) -> list[Fallback]:
    out: list[Fallback] = []
    earliest = deadlines.latest_start_meeting(rule, as_of)
    if earliest is not None:
        out.append(Fallback(kind="move_date", earliest_date=earliest,
                            text=f"Move the event to {_fmt(earliest)} or later to meet this deadline, then check the new date again."))
    droppable = [name for name in triggered_by if name != facts.venue and name != "usg_funding"]
    if droppable:
        what = "; ".join(_describe(ruleset, name) for name in droppable)
        out.append(Fallback(kind="change_format", text=f"Change the format so this rule no longer applies (without: {what})."))
    elif facts.venue in triggered_by:
        out.append(Fallback(kind="change_format", text="Choose a different kind of venue; each venue has its own steps and lead times."))
    if rule.domain == "funding":
        out.append(Fallback(kind="other_funding", text="Plan the event without USG funding (club money, an in-kind sponsor or a co-host), or ask USG at usgfunds@usc.edu."))
    return out


def build_packet(facts: EventFacts, ruleset: RuleSet, calendar: AcademicCalendar, as_of: date) -> EventPacket:
    known = known_names(ruleset)
    unknown = sorted({*facts.attributes, *facts.possible_attributes} - known)
    if unknown:
        raise UnknownAttribute(f"unknown attribute(s): {', '.join(unknown)}; use names from rules/vocabulary.json")

    confirmed = set(facts.attributes) | ({facts.venue} if facts.venue else set())
    possible = set(facts.possible_attributes) - confirmed
    everything = confirmed | possible
    certain_rules = {rule.id for rule in select_rules(ruleset, confirmed)}

    obligations: list[PacketObligation] = []
    start, end = facts.event_date, facts.end_date
    for rule in select_rules(ruleset, everything):
        from_possible = rule.id not in certain_rules
        triggered_by = [t for t in rule.triggers if t in everything]
        note: str | None = None
        unsure = from_possible
        green = False

        violated: bool | None = False
        fact = rule.params.get("violated_when")
        if isinstance(fact, str):
            if fact in confirmed:
                violated = True
                note = f"As described, the event has this: {_describe(ruleset, fact)}."
            elif fact in possible:
                violated, unsure = False, True
                note = f"Greenlight was not sure whether this applies: {_describe(ruleset, fact)}. Confirm it."
        elif rule.kind == "ineligible":
            violated = not from_possible
            note = f"USG does not fund this: {', '.join(_describe(ruleset, t) for t in triggered_by)}."
        elif rule.id in DATE_CHECKED:
            check = _date_check(rule, facts, calendar)
            note = check.note
            if check.violated is None:
                violated, unsure = False, True
            else:
                violated = check.violated
                unsure = unsure or check.confirm
                green = not check.violated and not check.confirm and facts.event_date is not None
        if from_possible:
            names = ", ".join(_describe(ruleset, t) for t in triggered_by if t in possible)
            note = f"Applies if the event has: {names}. Greenlight was not sure, so confirm it." + (f" {note}" if note else "")

        status = _status(ruleset, rule, violated, unsure=unsure)
        due = deadlines.due_date(rule, start=start, end=end)
        past_due = bool(due and due < as_of and rule.direction == "before")
        if past_due:
            note = (note + " " if note else "") + f"This was due on {_fmt(due)}, which has passed."  # type: ignore[arg-type]
        message = rule.message
        fix = _fix(rule)
        finding = _finding(ruleset, rule, status, note or message, fix, green=green and status == "condition", past_due=past_due)
        fallbacks = _fallbacks(ruleset, rule, as_of, triggered_by, facts) if (past_due or status == "blocked" or (violated and status == "check_with_office")) else []
        obligations.append(PacketObligation(
            rule_id=rule.id,
            title=rule.title,
            owner_office=rule.owner_office,
            status=status,
            status_label=STATUS_LABELS[status],
            due=due,
            due_note=_due_note(rule, facts, due),
            violated=bool(violated),
            past_due=past_due,
            message=message,
            note=note,
            fix=fix,
            finding=finding,
            citation=citation_for(ruleset, rule.id),
            link=rule.source_url,
            triggered_by=triggered_by,
            from_possible_attribute=from_possible,
            fallbacks=fallbacks,
        ))

    conflicts = _conflicts(ruleset, obligations)
    hard_blocks = _hard_blocks(facts, as_of, obligations)
    questions = _questions(ruleset, facts, possible)
    timeline = sorted(
        (TimelineEntry(day=o.due, rule_id=o.rule_id, title=o.title, status=o.status, past_due=o.past_due)
         for o in obligations if o.due is not None),
        key=lambda entry: (entry.day, entry.rule_id),
    )
    move_dates = [f.earliest_date for o in obligations if o.past_due for f in o.fallbacks if f.earliest_date]
    fallbacks: list[Fallback] = []
    if move_dates:
        latest = max(move_dates)
        fallbacks.append(Fallback(kind="move_date", earliest_date=latest,
                                  text=f"Every passed deadline is met if the event moves to {_fmt(latest)} or later. Check the new date again: it may fall in a blocked period."))
    if any(o.rule_id.startswith("usg-") and (o.status == "blocked" or o.past_due) for o in obligations):
        fallbacks.append(Fallback(kind="other_funding", text="USG funding is not possible as described. Plan the event with club money, an in-kind sponsor or a co-host, or ask USG at usgfunds@usc.edu."))
    counts = {status: sum(1 for o in obligations if o.status == status) for status in STATUS_LABELS}
    return EventPacket(
        as_of=as_of,
        event=facts,
        obligations=obligations,
        timeline=timeline,
        source_conflicts=conflicts,
        hard_blocks=hard_blocks,
        questions=questions,
        fallbacks=fallbacks,
        counts=counts,
        notice=PRECHECK_NOTICE,
    )


def _conflicts(ruleset: RuleSet, obligations: list[PacketObligation]) -> list[SourceConflict]:
    listed = {o.rule_id: o for o in obligations}
    seen: set[frozenset[str]] = set()
    out: list[SourceConflict] = []
    for o in obligations:
        rule = ruleset.get(o.rule_id)
        for other_id in rule.conflicts_with or []:
            pair = frozenset((rule.id, other_id))
            if other_id not in listed or pair in seen:
                continue
            seen.add(pair)
            other = ruleset.get(other_id)
            applied = deadlines.stricter_of(rule, other, o.due, listed[other_id].due)
            first = f"{rule.source} says {_lead_time(rule)}" if rule.kind == "deadline" else f"{rule.source}: {rule.message}"
            second = f"{other.source} says {_lead_time(other)}" if other.kind == "deadline" else f"{other.source}: {other.message}"
            if applied is None:
                result = "Greenlight cannot tell which is stricter for this event, so follow whichever comes first and check with the office."
            else:
                result = f"Greenlight applies the stricter one: {ruleset.get(applied).title}."
            out.append(SourceConflict(
                rules=[rule.id, other_id],
                applied=applied,
                explanation=f"Sources disagree. {first}; {second}. {result}",
                citations=[citation_for(ruleset, rule.id), citation_for(ruleset, other_id)],
            ))
    return out


def _hard_blocks(facts: EventFacts, as_of: date, obligations: Iterable[PacketObligation]) -> list[str]:
    blocks: list[str] = []
    if facts.event_date is not None and facts.event_date < as_of:
        blocks.append(f"The event date, {_fmt(facts.event_date)}, has already passed.")
    for o in obligations:
        if o.status == "blocked":
            blocks.append(f"{o.title}: {o.note or o.message}")
        elif o.past_due and o.status == "to_do":
            blocks.append(f"{o.title} was due on {_fmt(o.due)}, which has passed.")  # type: ignore[arg-type]
    return blocks


def _questions(ruleset: RuleSet, facts: EventFacts, possible: set[str]) -> list[str]:
    asks: dict[str, str] = {
        "event_date": "What date is the event? Greenlight needs it to date every deadline.",
        "end_date": "Does the event run over more than one day? If so, what is the last day?",
        "venue": "Where is the event: a Tutor Campus Center meeting room, a large Trojan Event Services venue, an outdoor space, a classroom, or off campus?",
        "headcount": "About how many people will come?",
        "attributes": "Some details of the event were unclear. Check the list of details below.",
    }
    out = [asks[name] for name in facts.needs_officer_input]
    if facts.event_date is None and "event_date" not in facts.needs_officer_input:
        out.append(asks["event_date"])
    if facts.venue is None and "venue" not in facts.needs_officer_input and "tabling" not in facts.attributes:
        out.append(asks["venue"])
    out.extend(f"Does the event have this: {_describe(ruleset, name)}?" for name in sorted(possible))
    return out

