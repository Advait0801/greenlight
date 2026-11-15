"""Evaluator for the year plan test set (Phase 4).

Each of the 2 plans goes through the year planner (code only; no AI). Three things are compared with the answer key:
  calendar  every (event, rule, status, due date) the key lists, against each event's packet in the plan;
  budget    the five totals the key fixes (total cost, money available, gap before USG, USG requested, requested
            over the yearly cap), exactly, in cents; and that every event's split adds up to its cost;
  problems  every expected problem (type, rule, severity and the set of events) must be found.

"caught" counts expected calendar entries and problems found; "missed" those absent or different; "wrongly_flagged"
calendar entries and problems the plan shows that the key does not expect.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from app.config import get_settings
from app.rules import RuleSet, get_calendar
from app.schemas.plans import PlanEvent, YearPlanReport, YearPlanRequest
from app.services.year_planner import plan_year

BUDGET_FIELDS = ("total_cost_cents", "funds_available_cents", "gap_before_usg_cents", "usg_requested_cents",
                 "usg_requested_over_yearly_cap_cents")


def request_for(case: dict[str, Any]) -> YearPlanRequest:
    plan = case["plan"]
    return YearPlanRequest(
        club_name=case["club"]["name"], mission=case["club"]["mission"], level=case["club"]["level"],
        money_on_hand_cents=plan["money_on_hand_cents"], expected_income_cents=plan["expected_income_cents"],
        usg_received_this_year_cents=plan["usg_received_this_year_cents"], unavailable_dates=plan["unavailable_dates"],
        events=[PlanEvent(**event) for event in case["events"]],
    )


def report_for(case: dict[str, Any], ruleset: RuleSet) -> YearPlanReport:
    return plan_year(request_for(case), ruleset, get_calendar(), date.fromisoformat(case["as_of"]),
                     get_settings().rules_dir / "sources")


def compare(report: YearPlanReport, expected: dict[str, Any]) -> dict[str, Any]:
    got_calendar = {(e.key, o.rule_id): (o.status, o.due.isoformat() if o.due else None)
                    for e in report.events for o in e.packet.obligations}
    want_calendar = {(c["event"], c["rule_id"]): (c["status"], c["due"]) for c in expected["calendar"]}
    calendar_missing = sorted(k for k in want_calendar if got_calendar.get(k) != want_calendar[k])
    calendar_extra = sorted(set(got_calendar) - set(want_calendar))

    budget = report.budget.model_dump()
    budget_diffs = {k: {"got": budget[k], "want": v} for k, v in expected["budget"].items() if budget.get(k) != v}
    split_ok = all(r.usg_planned_cents + r.club_money_cents + r.shortfall_cents == r.cost_cents for r in report.budget.rows)
    split_ok = split_ok and report.budget.total_cost_cents == (report.budget.usg_planned_cents + report.budget.club_money_cents
                                                               + report.budget.shortfall_cents)

    def key(p: Any) -> tuple[str, str | None, str, frozenset[str]]:
        if isinstance(p, dict):
            return (p["type"], p["rule_id"], p["severity"], frozenset(p["events"]))
        return (p.type, p.rule_id, p.severity.value, frozenset(p.events))

    got_problems = {key(p) for p in report.problems}
    want_problems = {key(p) for p in expected["problems"]}
    problems_missing = sorted(want_problems - got_problems, key=str)
    problems_extra = sorted(got_problems - want_problems, key=str)
    return {
        "calendar_found": len(want_calendar) - len(calendar_missing),
        "calendar_missing": calendar_missing,
        "calendar_extra": calendar_extra,
        "budget_diffs": budget_diffs,
        "split_adds_up": split_ok,
        "problems_found": len(want_problems) - len(problems_missing),
        "problems_missing": [list(map(str, p)) for p in problems_missing],
        "problems_extra": [list(map(str, p)) for p in problems_extra],
        "match": not (calendar_missing or calendar_extra or budget_diffs or problems_missing or problems_extra) and split_ok,
    }


def evaluate(data: dict[str, Any], ruleset: RuleSet) -> dict[str, Any]:
    rows = [{"id": case["id"], **compare(report_for(case, ruleset), case["expected"])} for case in data["cases"]]
    caught = sum(r["calendar_found"] + r["problems_found"] for r in rows)
    missed = sum(len(r["calendar_missing"]) + len(r["problems_missing"]) + len(r["budget_diffs"]) for r in rows)
    wrongly = sum(len(r["calendar_extra"]) + len(r["problems_extra"]) for r in rows)
    matched = sum(1 for r in rows if r["match"])
    notes = (f"{matched}/{len(rows)} plans match (calendar, budget totals and problems); "
             f"problems found {sum(r['problems_found'] for r in rows)}/{sum(r['problems_found'] + len(r['problems_missing']) for r in rows)}, "
             f"extra {sum(len(r['problems_extra']) for r in rows)}; budget totals exact in "
             f"{sum(1 for r in rows if not r['budget_diffs'])}/{len(rows)}; splits add up in "
             f"{sum(1 for r in rows if r['split_adds_up'])}/{len(rows)}")
    return {"caught": caught, "missed": missed, "wrongly_flagged": wrongly,
            "details": [r for r in rows if not r["match"]], "notes": notes}
