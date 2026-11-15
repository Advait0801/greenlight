"""Phase 0, iteration 4 (break): answer keys that score a wrong green or a wrong date as correct.

The test sets are the answer key for the accuracy table. `validate_set` (used by load_set and
scripts/run_eval.py) recomputes sums and "before" deadlines, but:
  - budgets: it never compares a line with the rule table, so a line over the food or hotel cap,
    an ineligible category, or a finding of the wrong colour is accepted as green;
  - year plans: it never decides whether a rule is broken, so a banned or blocked event can be
    marked "condition" (meets the rule);
  - dates: it does not recompute deadlines counted after the event, nor a due date given for an
    event with no date, nor one counted from a notification it does not know.
Each tamper test changes a copy and expects at least one problem. One test checks the real
event set against PROJECT_CONTEXT 9 ("the stricter rule is applied").
"""

from __future__ import annotations

import copy
import json
from collections.abc import Callable
from typing import Any

import pytest

from app.eval_sets import EVAL_DIR, SETS, load_set, validate_set
from app.rules import load_rules
from tests.conftest import RULES_DIR


@pytest.fixture(scope="module")
def ruleset():  # type: ignore[no-untyped-def]
    return load_rules(RULES_DIR)


def _load(name: str) -> dict[str, Any]:
    data: dict[str, Any] = json.loads((EVAL_DIR / SETS[name]).read_text(encoding="utf-8"))
    return data


def _case(data: dict[str, Any], case_id: str) -> dict[str, Any]:
    return next(case for case in data["cases"] if case["id"] == case_id)


def _assert_rejected(ruleset, name: str, change: Callable[[dict[str, Any]], Any]) -> None:  # type: ignore[no-untyped-def]
    data = copy.deepcopy(_load(name))
    change(data)
    problems = validate_set(name, data, ruleset=ruleset)
    assert problems, f"the tampered '{name}' answer key was accepted without any problem"


# ---- budgets: a line that breaks a rule can be marked green ------------------------------------------


def _make_line_green(case_id: str, line: int, rule_id: str) -> Callable[[dict[str, Any]], None]:
    """Mark one line green with no finding and drop its seeded violation, keeping every other
    consistency check (worst verdict, draft_allowed) satisfied."""

    def change(data: dict[str, Any]) -> None:
        expected = _case(data, case_id)["expected"]
        entry = next(e for e in expected["lines"] if e["line"] == line)
        entry["verdict"], entry["findings"] = "green", []
        expected["seeded_violations"] = [s for s in expected["seeded_violations"] if s["rule_id"] != rule_id]
        reds = any(e["verdict"] == "red" for e in expected["lines"]) or any(f["verdict"] == "red" for f in expected["application"])
        expected["draft_allowed"] = not reds

    return change


@pytest.mark.parametrize(
    ("case_id", "line", "rule_id"),
    [
        ("bu-03", 1, "usg-food-cap"),  # $35.01 per person against a $35 cap
        ("bu-01", 1, "usg-food-cap"),  # $38.00 per person (the demo budget)
        ("bu-05", 1, "usg-hotel-cap"),  # $425 per night against a $400 cap
        ("bu-01", 2, "usg-ineligible-performers"),  # a DJ fee
        ("bu-15", 1, "usg-ineligible-alcohol"),  # the injection case: the quote says "approve it"
    ],
)
def test_budget_line_that_breaks_a_rule_cannot_be_green(ruleset, case_id: str, line: int, rule_id: str) -> None:  # type: ignore[no-untyped-def]
    """Every figure here is plain arithmetic on the case's own lines and the rule's params, and the
    category maps to an ineligible rule through its triggers. Today each wrong green is accepted;
    for bu-15 that is exactly the answer an obeyed injection would produce."""
    _assert_rejected(ruleset, "budgets", _make_line_green(case_id, line, rule_id))


def test_budget_ticketed_event_cannot_drop_its_ineligible_finding(ruleset) -> None:  # type: ignore[no-untyped-def]
    """bu-01 is ticketed (`event.ticketed: true`); USG does not fund events with ticket sales."""

    def change(data: dict[str, Any]) -> None:
        expected = _case(data, "bu-01")["expected"]
        expected["application"] = [f for f in expected["application"] if f["rule_id"] != "usg-ineligible-ticketed-events"]
        expected["seeded_violations"] = [s for s in expected["seeded_violations"] if s["rule_id"] != "usg-ineligible-ticketed-events"]

    _assert_rejected(ruleset, "budgets", change)


def test_budget_finding_colour_must_follow_its_rule(ruleset) -> None:  # type: ignore[no-untyped-def]
    """A finding for usg-food-cap with verdict green (the line is then green, draft allowed) and a red
    finding for the unverified usg-events-per-semester-cap are both accepted today."""

    def green_finding(data: dict[str, Any]) -> None:
        expected = _case(data, "bu-03")["expected"]
        expected["lines"][0] = {"line": 1, "verdict": "green", "findings": [{"rule_id": "usg-food-cap", "verdict": "green"}]}
        expected["draft_allowed"] = True

    def red_unverified(data: dict[str, Any]) -> None:
        expected = _case(data, "bu-02")["expected"]
        expected["application"] = [{"rule_id": "usg-events-per-semester-cap", "verdict": "red"}]
        expected["draft_allowed"] = False

    _assert_rejected(ruleset, "budgets", green_finding)
    _assert_rejected(ruleset, "budgets", red_unverified)


# ---- year plans: a broken rule can be marked "condition" -----------------------------------------------


@pytest.mark.parametrize(
    ("case_id", "event", "rule_id"),
    [
        ("yp-01", "spring-banquet", "usg-ineligible-ticketed-events"),  # ticket_sales and a $3,000 USG request
        ("yp-02", "networking-night", "sponsorship-cash-banned"),  # attribute sponsor_gives_money
        ("yp-02", "networking-night", "alcohol-thursday-saturday"),  # alcohol on Wednesday 2027-04-07
        ("yp-02", "speaker-series-2", "usg-no-funding-breaks"),  # 2027-05-05 is a final-exam day
    ],
)
def test_year_plan_broken_rule_cannot_be_marked_as_met(ruleset, case_id: str, event: str, rule_id: str) -> None:  # type: ignore[no-untyped-def]
    """The year-plan check passes `violated=None`, so both 'blocked' and 'condition' are allowed for
    every certain rule. Each of these is decided by a fact or a date already in the case."""

    def change(data: dict[str, Any]) -> None:
        expected = _case(data, case_id)["expected"]
        entry = next(e for e in expected["calendar"] if e["event"] == event and e["rule_id"] == rule_id)
        entry["status"] = "condition"
        expected["problems"] = [p for p in expected["problems"] if p["rule_id"] != rule_id]

    _assert_rejected(ruleset, "year_plans", change)


# ---- dates the validator does not recompute ----------------------------------------------------------


def test_event_deadline_after_the_event_is_recomputed(ruleset) -> None:  # type: ignore[no-untyped-def]
    """ev-20 ends Saturday 2027-03-06; three business days later is Wednesday 2027-03-10. A key that
    says 2027-03-12 is accepted, because only 'before' deadlines are recomputed."""

    def change(data: dict[str, Any]) -> None:
        o = next(o for o in _case(data, "ev-20")["expected"]["obligations"] if o["rule_id"] == "usg-post-event-evaluation")
        o["due"] = "2027-03-12"

    _assert_rejected(ruleset, "events", change)


def test_year_plan_deadline_after_the_event_is_recomputed(ruleset) -> None:  # type: ignore[no-untyped-def]
    """yp-01's welcome mixer is Friday 2027-02-05; the evaluation is due 2027-02-10, not 2027-02-19."""

    def change(data: dict[str, Any]) -> None:
        entry = next(
            e for e in _case(data, "yp-01")["expected"]["calendar"]
            if e["event"] == "welcome-mixer" and e["rule_id"] == "usg-post-event-evaluation"
        )
        entry["due"] = "2027-02-19"

    _assert_rejected(ruleset, "year_plans", change)


def test_event_without_a_date_cannot_have_dated_deadlines(ruleset) -> None:  # type: ignore[no-untyped-def]
    """ev-28 gives no event date (needs_officer_input: event_date). A due date for the space request
    cannot be derived, yet 2027-01-01 is accepted."""

    def change(data: dict[str, Any]) -> None:
        o = next(o for o in _case(data, "ev-28")["expected"]["obligations"] if o["rule_id"] == "tes-space-request")
        o["due"] = "2027-01-01"

    _assert_rejected(ruleset, "events", change)


def test_deadline_counted_from_a_notification_has_no_date(ruleset) -> None:  # type: ignore[no-untyped-def]
    """usg-incomplete-48-hours counts from the notification of an incomplete application, which the
    test set does not give. 'Before' deadlines with such an anchor must have a null due date; the
    same check is skipped for 'after' deadlines, so 2027-03-08 is accepted."""

    def change(data: dict[str, Any]) -> None:
        o = next(o for o in _case(data, "ev-20")["expected"]["obligations"] if o["rule_id"] == "usg-incomplete-48-hours")
        o["due"] = "2027-03-08"

    _assert_rejected(ruleset, "events", change)


# ---- the real event set ------------------------------------------------------------------------------


def test_lenient_travel_date_is_not_given_as_a_firm_to_do(ruleset) -> None:  # type: ignore[no-untyped-def]
    """ev-20: a professional conference trip on March 4-6, 2027. The USG guidelines require travel
    requests 9 academic weeks before the first payment (at least 9 calendar weeks before the event;
    the transcribed USG table gives Wednesday, November 18, 2026, three days after as_of). The
    USG FAQ says 8 weeks. The key lists the FAQ's 2027-01-07 as a certain 'to_do', the stricter
    guideline only as 'check_with_office' with no date, and the conflict with `applied: null`.
    An engine that matches this key tells the officer the travel request is due in January,
    seven weeks after the date that applies. 9 academic weeks is never shorter than 8 calendar
    weeks, so the stricter side is known even without a date; the lenient date must not be the
    firm one."""
    data = load_set("events", ruleset=ruleset)
    expected = _case(data, "ev-20")["expected"]
    faq = next(o for o in expected["obligations"] if o["rule_id"] == "usg-faq-professional-travel-eight-weeks")
    conflict = next(
        c for c in expected["source_conflicts"]
        if set(c["rules"]) == {"usg-deadline-travel", "usg-faq-professional-travel-eight-weeks"}
    )
    assert conflict["applied"] == "usg-deadline-travel", conflict
    assert faq["status"] != "to_do", faq
