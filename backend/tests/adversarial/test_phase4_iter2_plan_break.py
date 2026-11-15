"""Phase 4, iteration 2 (break): the year plan.

Each test describes the correct behaviour (PROJECT_CONTEXT 4A, 7 "USG funding", 9; CLAUDE.md trust rules; PLAN.md
Phase 4 exit criteria) and fails against main at dbf5c5e. Everything here is code only; no AI call is made.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from app.config import REPO_ROOT
from app.rules import get_calendar, get_ruleset
from app.schemas.common import Verdict
from app.schemas.plans import PlanEvent, YearPlanReport, YearPlanRequest
from app.services.year_planner import plan_year

AS_OF = date(2026, 11, 15)
SOURCES = REPO_ROOT / "rules" / "sources"


def _event(key: str, day: str | None = "2027-04-09", **extra: Any) -> PlanEvent:
    base: dict[str, Any] = {"key": key, "name": key, "event_date": day, "venue": "venue_classroom", "headcount": 30,
                            "attributes": ["food"], "estimated_cost_cents": 100000, "usg_request_cents": 50000}
    base.update(extra)
    return PlanEvent(**base)


def _plan(events: list[PlanEvent], as_of: date = AS_OF, **extra: Any) -> YearPlanReport:
    fields: dict[str, Any] = {"money_on_hand_cents": 0, "expected_income_cents": 0, "usg_received_this_year_cents": 0}
    fields.update(extra)
    return plan_year(YearPlanRequest(events=events, **fields), get_ruleset(), get_calendar(), as_of, SOURCES)


# ---- [blocker] yearly cap bypassed by a Summer Session 2027 event dated July or August


def test_summer_session_event_in_july_counts_against_the_2026_27_yearly_cap() -> None:
    # Rule usg-yearly-cap: "Section 3: Maximum Funding per Academic Year"; Summer Session 2027 (May 19 - Aug 10, 2027)
    # is part of USC's 2026-27 academic calendar (rules/calendar.json). With the full $8,000 already received in
    # 2026-27, nothing more fits; the plan must not say "Within the yearly cap".
    report = _plan([_event("summer", "2027-07-15", estimated_cost_cents=300000, usg_request_cents=300000)],
                   usg_received_this_year_cents=800000)
    planned = sum(s.planned_cents for s in report.strategy.steps)
    assert planned == 0, f"planned {planned} cents of USG money although the 2026-27 cap is used up"
    assert any(p.type == "over_yearly_cap" and "summer" in p.events for p in report.problems)
    assert report.budget.usg_requested_over_yearly_cap_cents == 300000


# ---- [blocker] summer events planned as USG money and counted in the budget


def test_summer_event_is_not_counted_as_planned_usg_money() -> None:
    # Rule usg-faq-no-summer-funding (yellow) says USG does not fund summer events; the deadline table has no row for
    # summer. Unsure must be yellow, so the plan cannot count the money as covering the event ("Every event is
    # covered on paper") with a plain "apply" step.
    for day in ("2027-06-15", "2027-07-15"):
        report = _plan([_event("summer", day, estimated_cost_cents=300000, usg_request_cents=300000)])
        assert "summer" not in {s.key for s in report.strategy.steps}, day
        not_planned = {n.key: n for n in report.strategy.not_planned}
        assert "summer" in not_planned and not_planned["summer"].severity is Verdict.YELLOW, day
        assert report.budget.shortfall_cents == 300000, day


# ---- [high] a merged problem keeps the first event's severity, hiding a red


def test_merged_problem_shows_the_worst_severity_of_its_events() -> None:
    maybe = _event("maybe", "2026-11-17", venue="venue_outdoor", attributes=[], possible_attributes=["minors"],
                   usg_request_cents=0)
    sure = _event("sure", "2026-11-17", venue="venue_outdoor", attributes=["minors"], usg_request_cents=0)
    report = _plan([maybe, sure])
    sure_packet = next(e for e in report.events if e.key == "sure").packet
    minors = next(o for o in sure_packet.obligations if o.rule_id == "minors-registration")
    assert minors.past_due and minors.finding is not None and minors.finding.verdict is Verdict.RED
    problem = next(p for p in report.problems if p.rule_id == "minors-registration")
    assert "sure" in problem.events
    assert problem.severity is Verdict.RED, "a certain missed deadline is shown as 'to check'"


# ---- [high] office-decides items silently missing from the plan


def test_multi_day_event_asking_usg_lists_the_case_by_case_review() -> None:
    # The officer gave an end date after the start date, so the event is multi-day for certain.
    report = _plan([_event("trip", "2027-04-06", end_date="2027-04-08")])
    rule_ids = {o.rule_id for o in report.events[0].packet.obligations}
    assert "usg-multi-day-case-by-case" in rule_ids


def test_event_costing_over_4000_asking_usg_lists_the_case_by_case_review() -> None:
    # "Events with expenses over $4,000 will be reviewed on a case-by-case basis" (usg-over-4000-case-by-case). The
    # plan knows the estimated cost (the demo's culture night costs $7,070).
    report = _plan([_event("big", "2027-04-06", estimated_cost_cents=500000, usg_request_cents=300000)])
    rule_ids = {o.rule_id for o in report.events[0].packet.obligations}
    assert "usg-over-4000-case-by-case" in rule_ids


# ---- [medium] possibly-ineligible event planned as certain USG money


def test_event_possibly_ticketed_is_not_planned_as_certain_usg_money() -> None:
    report = _plan([_event("maybe-tickets", "2027-04-09", possible_attributes=["ticket_sales"])])
    step = next((s for s in report.strategy.steps if s.key == "maybe-tickets"), None)
    not_planned = {n.key: n for n in report.strategy.not_planned}
    flagged_step = step is not None and "ticket" in step.note.lower()
    flagged_out = "maybe-tickets" in not_planned and not_planned["maybe-tickets"].severity is Verdict.YELLOW
    assert flagged_step or flagged_out, "USG money planned with 'Within the yearly cap.' although tickets may be sold"


# ---- [medium] budget over-cap figure and problem list disagree for an undated event


def test_over_cap_figure_and_over_cap_problem_agree() -> None:
    report = _plan([_event("undated", None, estimated_cost_cents=500000, usg_request_cents=500000),
                    _event("dated", "2027-04-09", estimated_cost_cents=500000, usg_request_cents=500000)])
    over = report.budget.usg_requested_over_yearly_cap_cents
    has_problem = any(p.type == "over_yearly_cap" for p in report.problems)
    assert ((over or 0) > 0) == has_problem, f"budget says {over} cents over the cap; over_yearly_cap problem: {has_problem}"


# ---- [medium] "this week" tells the officer to apply to USG for an event USG cannot fund


def test_this_week_does_not_ask_to_apply_to_usg_for_an_event_usg_cannot_fund() -> None:
    report = _plan([_event("tickets", "2027-04-09", attributes=["food", "ticket_sales"])])
    assert any(n.key == "tickets" and n.severity is Verdict.RED for n in report.strategy.not_planned)
    assert not any(item.kind == "usg_table" and item.event_key == "tickets" for item in report.this_week)
