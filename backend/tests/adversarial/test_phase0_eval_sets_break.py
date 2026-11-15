"""Phase 0, iteration 2 (break): malformed and inconsistent test-set data.

The test sets are the answer key for the accuracy table. An answer key that lists a wrong
figure, a wrong due date, a less strict rule as "applied", a green uncertainty or a missing
obligation would score a wrong engine as right. Each test tampers with a copy and expects
validate_set (which `scripts/run_eval.py` and load_set use) to report it, or checks the real
data against the method the set documents.
"""

from __future__ import annotations

import copy
import json
import shutil
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from app.eval_sets import EVAL_DIR, SETS, EvalSetError, load_set, validate_set
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


def _obligation(case: dict[str, Any], rule_id: str) -> dict[str, Any]:
    return next(o for o in case["expected"]["obligations"] if o["rule_id"] == rule_id)


def _assert_rejected(ruleset, name: str, change: Callable[[dict[str, Any]], Any]) -> None:  # type: ignore[no-untyped-def]
    data = copy.deepcopy(_load(name))
    change(data)
    problems = validate_set(name, data, ruleset=ruleset)
    assert problems, f"the tampered '{name}' test set was accepted without any problem"


# ---- year plans ----------------------------------------------------------------------------------


def test_year_plan_over_cap_figure_is_checked(ruleset) -> None:  # type: ignore[no-untyped-def]
    """budget.usg_requested_over_yearly_cap_cents is the only budget figure not recomputed.
    yp-01 asks USG for $11,250 against an $8,000 cap; an answer key saying 0 is accepted today."""

    def change(d: dict[str, Any]) -> None:
        _case(d, "yp-01")["expected"]["budget"]["usg_requested_over_yearly_cap_cents"] = 0

    _assert_rejected(ruleset, "year_plans", change)


def test_year_plan_over_cap_needs_an_over_cap_problem(ruleset) -> None:  # type: ignore[no-untyped-def]
    """An amount over the yearly cap with no over_yearly_cap problem is a silently missing finding."""

    def change(d: dict[str, Any]) -> None:
        expected = _case(d, "yp-01")["expected"]
        expected["problems"] = [p for p in expected["problems"] if p["type"] != "over_yearly_cap"]

    _assert_rejected(ruleset, "year_plans", change)


def test_year_plan_wrong_due_date_is_rejected(ruleset) -> None:  # type: ignore[no-untyped-def]
    """welcome-mixer is on 2027-02-05; approvals-two-weeks is due 2027-01-22. Nothing (validator or
    test) checks year-plan due dates against the rule lead times, so a wrong date is accepted."""

    def change(d: dict[str, Any]) -> None:
        entry = next(
            e for e in _case(d, "yp-01")["expected"]["calendar"]
            if e["event"] == "welcome-mixer" and e["rule_id"] == "approvals-two-weeks"
        )
        entry["due"] = "2027-01-29"

    _assert_rejected(ruleset, "year_plans", change)


def test_year_plan_unverified_rule_cannot_be_to_do(ruleset) -> None:  # type: ignore[no-untyped-def]
    """usg-no-funding-breaks rests on the unverified calendar, so it must be check_with_office.
    The event set enforces this in a test; the year plans are not checked at all."""

    def change(d: dict[str, Any]) -> None:
        entry = next(
            e for e in _case(d, "yp-01")["expected"]["calendar"]
            if e["event"] == "welcome-mixer" and e["rule_id"] == "usg-no-funding-breaks"
        )
        entry["status"] = "to_do"

    _assert_rejected(ruleset, "year_plans", change)


IN_SCOPE = {"deadline", "requirement", "cap", "banned", "blocked_period"}


def test_year_plan_calendar_lists_every_triggered_obligation(ruleset) -> None:  # type: ignore[no-untyped-def]
    """The year-plan set says its calendar uses 'the same scope and method as the event test set'.
    Applying that method (tests/unit/test_eval_sets.py::test_event_obligations_agree_with_rule_triggers)
    to the year plans: yp-02 'networking-night' serves alcohol and asks USG for $1,000, so
    usg-ineligible-alcohol applies, but the answer key leaves it out."""
    for case in _load("year_plans")["cases"]:
        for event in case["events"]:
            present = set(event["attributes"]) | {event["venue"]}
            if event["usg_request_cents"] > 0:
                present.add("usg_funding")
            derived = set()
            for rule in ruleset:
                if not rule.triggers:
                    continue
                in_scope = (rule.domain in ("events", "outside_money") and rule.kind in IN_SCOPE) or (
                    rule.domain == "funding" and "usg_funding" in present
                    and rule.kind in {"deadline", "blocked_period", "ineligible"}
                )
                if not in_scope:
                    continue
                triggers = [t in present for t in rule.triggers]
                if all(triggers) if rule.trigger_mode == "all" else any(triggers):
                    derived.add(rule.id)
            listed = {e["rule_id"] for e in case["expected"]["calendar"] if e["event"] == event["key"]}
            assert listed == derived, (case["id"], event["key"], sorted(derived - listed), sorted(listed - derived))


# ---- events --------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("case_id", "rule_id", "past_due"),
    [("ev-12", "approvals-two-weeks", False), ("ev-01", "approvals-two-weeks", True)],
    ids=["overdue-marked-not-past-due", "future-marked-past-due"],
)
def test_event_past_due_must_follow_due_and_as_of(ruleset, case_id: str, rule_id: str, past_due: bool) -> None:  # type: ignore[no-untyped-def]
    """ev-12 (as of 2026-11-15) has approvals due 2026-11-02: past due. ev-01's are due 2027-03-26:
    not past due. Flipping either flag is accepted today."""
    _assert_rejected(ruleset, "events", lambda d: _obligation(_case(d, case_id), rule_id).update(past_due=past_due))


def test_event_conflict_must_apply_the_stricter_rule(ruleset) -> None:  # type: ignore[no-untyped-def]
    """PROJECT_CONTEXT 9: 'the stricter rule is applied and both are cited'. ev-01: the FAQ's 4-week
    cancellation (due 2027-03-12) is stricter than the terms' 3 weeks (2027-03-19). An answer key
    naming the 3-week rule as applied is accepted today."""
    _assert_rejected(
        ruleset, "events",
        lambda d: _case(d, "ev-01")["expected"]["source_conflicts"][0].update(applied="tes-cancellation-large-terms"),
    )


def test_event_conflict_applied_must_be_one_of_the_pair(ruleset) -> None:  # type: ignore[no-untyped-def]
    _assert_rejected(
        ruleset, "events",
        lambda d: _case(d, "ev-01")["expected"]["source_conflicts"][0].update(applied="usg-food-cap"),
    )


def test_event_conflict_between_listed_obligations_cannot_be_dropped(ruleset) -> None:  # type: ignore[no-untyped-def]
    """Both cancellation rules are listed for ev-01 and they conflict in the rule table; an answer key
    with no source_conflicts entry hides the disagreement and is accepted today."""
    _assert_rejected(ruleset, "events", lambda d: _case(d, "ev-01")["expected"].update(source_conflicts=[]))


# ---- budgets -------------------------------------------------------------------------------------


def test_budget_uncertainty_findings_are_always_yellow(ruleset) -> None:  # type: ignore[no-untyped-def]
    """budgets.schema.json: reasons other than 'rule' 'are uncertainties that always mean yellow'.
    bu-14 (attendance 0, per-person cost cannot be computed) marked green is accepted today."""

    def change(d: dict[str, Any]) -> None:
        line = _case(d, "bu-14")["expected"]["lines"][0]
        line["verdict"] = "green"
        line["findings"][0]["verdict"] = "green"

    _assert_rejected(ruleset, "budgets", change)


def test_budget_line_cannot_be_greener_than_its_findings(ruleset) -> None:  # type: ignore[no-untyped-def]
    """bu-03 line 1 is $35.01 per person, a red usg-food-cap finding. Marking the line green (and
    allowing the draft) is accepted today: draft_allowed only looks at line verdicts."""

    def change(d: dict[str, Any]) -> None:
        case = _case(d, "bu-03")
        case["expected"]["lines"][0]["verdict"] = "green"
        case["expected"]["draft_allowed"] = True

    _assert_rejected(ruleset, "budgets", change)


def test_budget_rule_finding_needs_a_rule_id(ruleset) -> None:  # type: ignore[no-untyped-def]
    """A finding with reason 'rule' (the default) and no rule_id carries no rule text or source."""
    _assert_rejected(
        ruleset, "budgets", lambda d: _case(d, "bu-03")["expected"]["lines"][0]["findings"][0].update(rule_id=None)
    )


def test_budget_seeded_violation_needs_a_matching_finding(ruleset) -> None:  # type: ignore[no-untyped-def]
    """bu-03 seeds a usg-food-cap violation on line 1. Removing the finding (line green, draft
    allowed) while keeping the seeded violation is accepted today."""

    def change(d: dict[str, Any]) -> None:
        case = _case(d, "bu-03")
        case["expected"]["lines"][0].update(verdict="green", findings=[])
        case["expected"]["draft_allowed"] = True

    _assert_rejected(ruleset, "budgets", change)


# ---- files ---------------------------------------------------------------------------------------


@pytest.fixture
def eval_copy(tmp_path: Path) -> Path:
    target = tmp_path / "eval"
    shutil.copytree(EVAL_DIR, target)
    return target


def test_set_file_that_is_not_utf8_is_an_eval_set_error(eval_copy: Path) -> None:
    """Currently raises UnicodeDecodeError."""
    (eval_copy / "events" / "cases.json").write_bytes(b"\xff\xfe{")
    with pytest.raises(EvalSetError):
        load_set("events", eval_dir=eval_copy)


def test_constitution_text_that_is_not_utf8_is_an_eval_set_error(eval_copy: Path, ruleset) -> None:  # type: ignore[no-untyped-def]
    """Currently raises UnicodeDecodeError."""
    (eval_copy / "constitutions" / "texts" / "co-01.txt").write_bytes(b"\xff\xfe\x00\x00 scanned garbage")
    with pytest.raises(EvalSetError):
        load_set("constitutions", eval_dir=eval_copy, ruleset=ruleset)


def test_missing_schema_is_an_eval_set_error(eval_copy: Path) -> None:
    """Currently raises FileNotFoundError."""
    (eval_copy / "schemas" / "events.schema.json").unlink()
    with pytest.raises(EvalSetError):
        load_set("events", eval_dir=eval_copy)
