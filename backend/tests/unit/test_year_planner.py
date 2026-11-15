"""The year planner: calendar, budget, funding strategy, problems and 'this week', all from code."""

from __future__ import annotations

import ast
import json
from datetime import date
from typing import Any

import pytest
from pydantic import ValidationError

from app.config import REPO_ROOT
from app.rules import get_calendar, get_ruleset
from app.schemas.common import Verdict
from app.schemas.plans import PlanEvent, YearPlanReport, YearPlanRequest
from app.services import usg_deadline_table
from app.services.year_planner import plan_year

AS_OF = date(2026, 11, 15)
CASES = json.loads((REPO_ROOT / "data" / "eval" / "year_plans" / "cases.json").read_text(encoding="utf-8"))["cases"]
SOURCES = REPO_ROOT / "rules" / "sources"


def _event(key: str, day: str | None = "2027-04-09", **extra: Any) -> PlanEvent:
    base: dict[str, Any] = {"key": key, "name": key.replace("-", " ").title(), "event_date": day, "venue": "venue_outdoor",
                            "headcount": 50, "attributes": ["food"], "estimated_cost_cents": 100000, "usg_request_cents": 50000}
    base.update(extra)
    return PlanEvent(**base)


def _plan(events: list[PlanEvent], as_of: date = AS_OF, **extra: Any) -> YearPlanReport:
    fields: dict[str, Any] = {"money_on_hand_cents": 100000, "expected_income_cents": 0, "usg_received_this_year_cents": 0}
    fields.update(extra)
    return plan_year(YearPlanRequest(events=events, **fields), get_ruleset(), get_calendar(), as_of, SOURCES)


def _case(case_id: str) -> YearPlanReport:
    case = next(c for c in CASES if c["id"] == case_id)
    plan = case["plan"]
    request = YearPlanRequest(
        money_on_hand_cents=plan["money_on_hand_cents"], expected_income_cents=plan["expected_income_cents"],
        usg_received_this_year_cents=plan["usg_received_this_year_cents"], unavailable_dates=plan["unavailable_dates"],
        events=[PlanEvent(**e) for e in case["events"]])
    return plan_year(request, get_ruleset(), get_calendar(), date.fromisoformat(case["as_of"]), SOURCES)


def _types(report: YearPlanReport) -> set[tuple[str, str | None]]:
    return {(p.type, p.rule_id) for p in report.problems}


# ---- the demo story


def test_demo_retreat_travel_deadline_lands_in_november_of_the_previous_semester() -> None:
    report = _case("yp-01")
    retreat = next(e for e in report.events if e.key == "retreat")
    travel = next(d for d in retreat.usg_deadlines if d.rule_id == "usg-deadline-travel")
    assert travel.table_date == date(2026, 11, 18)
    assert travel.latest_possible == date(2026, 12, 25)
    assert travel.latest_possible_in == "winter recess"
    assert travel.before_semester
    problem = next(p for p in report.problems if p.rule_id == "usg-deadline-travel")
    assert problem.severity is Verdict.YELLOW
    assert "November 18, 2026" in problem.note and "not yet confirmed" in problem.note
    assert [c.rule_id for c in problem.also_cites] == ["usg-academic-week-definition"]
    # The first thing to do this week is that application, marked as a date to confirm with USG.
    first = report.this_week[0]
    assert first.day == date(2026, 11, 18) and first.unconfirmed and first.kind == "usg_table"


def test_semester_cap_is_yellow_never_a_silent_block_and_the_strategy_keeps_to_it() -> None:
    report = _case("yp-01")
    cap = next(p for p in report.problems if p.type == "funded_events_over_semester_cap")
    assert cap.severity is Verdict.YELLOW and len(cap.events) == 5
    assert "confirm" in cap.note.lower()
    per_term: dict[str | None, int] = {}
    for step in report.strategy.steps:
        per_term[step.term] = per_term.get(step.term, 0) + 1
    assert all(count <= 4 for count in per_term.values())


def test_strategy_never_plans_more_than_the_yearly_cap() -> None:
    for case_id, received in (("yp-01", 0), ("yp-02", 500000)):
        report = _case(case_id)
        planned = sum(step.planned_cents for step in report.strategy.steps)
        assert received + planned <= 800000
        assert all(step.planned_cents <= step.requested_cents for step in report.strategy.steps)


def test_ticketed_event_is_left_out_of_the_funding_plan_with_its_rule() -> None:
    report = _case("yp-01")
    banquet = next(n for n in report.strategy.not_planned if n.key == "spring-banquet")
    assert banquet.citation is not None and banquet.citation.rule_id == "usg-ineligible-ticketed-events"
    assert all(step.key != "spring-banquet" for step in report.strategy.steps)


def test_largest_requests_are_planned_first() -> None:
    report = _case("yp-01")
    amounts = [step.requested_cents for step in report.strategy.steps]
    assert amounts == sorted(amounts, reverse=True)


# ---- budget


@pytest.mark.parametrize("case_id", ["yp-01", "yp-02"])
def test_budget_totals_are_exact_and_every_split_adds_up(case_id: str) -> None:
    case = next(c for c in CASES if c["id"] == case_id)
    budget = _case(case_id).budget
    for key, value in case["expected"]["budget"].items():
        assert getattr(budget, key) == value, key
    for row in budget.rows:
        assert row.usg_planned_cents + row.club_money_cents + row.shortfall_cents == row.cost_cents
        assert min(row.usg_planned_cents, row.club_money_cents, row.shortfall_cents) >= 0
    assert budget.total_cost_cents == budget.usg_planned_cents + budget.club_money_cents + budget.shortfall_cents
    assert budget.club_money_cents + budget.unallocated_cents == budget.funds_available_cents
    assert budget.usg_planned_cents == sum(s.planned_cents for s in _case(case_id).strategy.steps)


def test_club_money_goes_to_earlier_events_first() -> None:
    report = _plan([_event("late", "2027-04-20", usg_request_cents=0), _event("early", "2027-03-02", usg_request_cents=0)],
                   money_on_hand_cents=150000)
    rows = {r.key: r for r in report.budget.rows}
    assert rows["early"].club_money_cents == 100000 and rows["late"].club_money_cents == 50000
    assert rows["late"].shortfall_cents == 50000


def test_unknown_usg_received_is_asked_never_assumed_zero() -> None:
    report = _plan([_event("one")], usg_received_this_year_cents=None)
    assert report.budget.usg_requested_over_yearly_cap_cents is None
    problem = next(p for p in report.problems if p.type == "yearly_cap_unknown")
    assert problem.severity is Verdict.YELLOW
    assert any("received from USG" in q for q in report.questions)


def test_request_above_cost_is_refused() -> None:
    with pytest.raises(ValidationError):
        _event("x", estimated_cost_cents=100, usg_request_cents=200)


def test_duplicate_event_keys_are_refused() -> None:
    with pytest.raises(ValidationError):
        YearPlanRequest(events=[_event("a"), _event("a")])


# ---- problems


def test_same_day_requests_and_unavailable_officers() -> None:
    report = _plan([_event("a", "2027-03-03"), _event("b", "2027-03-03"), _event("c", "2027-03-04", usg_request_cents=0)],
                   unavailable_dates=[date(2027, 3, 4)])
    same = next(p for p in report.problems if p.type == "same_day_funding_requests")
    assert sorted(same.events) == ["a", "b"] and same.severity is Verdict.YELLOW
    away = next(p for p in report.problems if p.type == "officers_unavailable")
    assert away.events == ["c"] and away.rule_id is None


def test_spring_event_in_january_has_passed_its_table_deadline() -> None:
    report = _plan([_event("jan", "2027-01-20")])
    passed = next(p for p in report.problems if p.type == "usg_deadline_passed_per_table")
    assert passed.severity is Verdict.YELLOW and "November 11, 2026" in passed.note
    assert any(n.key == "jan" for n in report.strategy.not_planned)


def test_event_in_spring_recess_is_blocked_by_the_packet_rule() -> None:
    report = _plan([_event("recess", "2027-03-17")])
    assert ("event_in_blocked_period", "usg-no-funding-breaks") in _types(report)


def test_no_events_gives_an_empty_plan() -> None:
    report = _plan([])
    assert report.events == [] and report.problems == [] and report.this_week == []
    assert report.budget.total_cost_cents == 0 and report.budget.unallocated_cents == 100000


def test_event_without_a_date_is_asked_about_and_not_planned_for_usg() -> None:
    report = _plan([_event("undated", None)])
    assert ("event_needs_date", None) in _types(report)
    assert report.strategy.steps == [] and report.strategy.not_planned[0].key == "undated"


def test_editing_an_event_recomputes_everything() -> None:
    before = _plan([_event("a", "2027-02-05"), _event("b", "2027-04-09")])
    after = _plan([_event("a", "2027-04-14"), _event("b", "2027-04-09")])
    assert ("deadline_in_previous_semester_or_break", "usg-page-deadline-event-date") in _types(before)
    assert ("deadline_in_previous_semester_or_break", "usg-page-deadline-event-date") not in _types(after)
    assert all(item.day != date(2026, 11, 18) for item in after.calendar)
    deleted = _plan([_event("b", "2027-04-09")])
    assert {item.event_key for item in deleted.calendar} == {"b"}
    assert [row.key for row in deleted.budget.rows] == ["b"]


def test_problem_findings_carry_their_rule_citation() -> None:
    for case_id in ("yp-01", "yp-02"):
        for p in _case(case_id).problems:
            if p.rule_id is not None:
                assert p.citation is not None and p.citation.rule_id == p.rule_id
                assert p.finding is not None and p.finding.verdict is p.severity
            assert p.severity is not Verdict.GREEN


# ---- the deadline table copy


def test_table_lookup_uses_the_monday_row_for_a_weekend() -> None:
    ruleset = get_ruleset()
    saturday = usg_deadline_table.lookup(ruleset, SOURCES, date(2027, 2, 27), "9_week")
    assert saturday.status == "date" and saturday.deadline == date(2026, 11, 18)
    recess = usg_deadline_table.lookup(ruleset, SOURCES, date(2027, 3, 17), "6_week")
    assert recess.status == "no_deadline"
    may = usg_deadline_table.lookup(ruleset, SOURCES, date(2027, 5, 20), "6_week")
    assert may.status == "not_in_table"
    fall = usg_deadline_table.lookup(ruleset, SOURCES, date(2026, 9, 2), "6_week")
    assert fall.status == "not_applicable"


def test_planner_reuses_the_phase_2_and_3_engines() -> None:
    source = (REPO_ROOT / "backend" / "app" / "services" / "year_planner.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported = {alias.name for node in ast.walk(tree) if isinstance(node, ast.ImportFrom) for alias in node.names}
    assert {"build_packet", "match_fund", "limit_cents", "money", "deadlines"} <= imported
    # No rule caps or lead times written into the planner: they are read from the rule table.
    assert "8000" not in source and "800000" not in source and "= 4\n" not in source



# ---- regressions from iteration 1 (verify)


def test_unknown_received_amount_still_caps_the_funding_plan() -> None:
    """H1: with the amount received left empty, five $3,000 requests were all planned ($12,000 for one year)."""
    events = [_event(f"e{i}", f"2027-04-{5 + i:02d}", estimated_cost_cents=300000, usg_request_cents=300000) for i in range(5)]
    report = _plan(events, usg_received_this_year_cents=None)
    planned = sum(step.planned_cents for step in report.strategy.steps)
    assert planned <= 800000
    assert any("not known" in step.note for step in report.strategy.steps)
    assert report.budget.usg_planned_cents == planned


def test_over_yearly_cap_figure_is_counted_per_academic_year() -> None:
    """M: $5,000 in spring 2027 and $5,000 in fall 2027 is not over either year's cap."""
    events = [_event("spring", "2027-04-07", estimated_cost_cents=500000, usg_request_cents=500000),
              _event("fall", "2027-10-06", estimated_cost_cents=500000, usg_request_cents=500000)]
    report = _plan(events)
    assert report.budget.usg_requested_over_yearly_cap_cents == 0
    assert all(p.type != "over_yearly_cap" for p in report.problems)
