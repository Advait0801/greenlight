"""Evaluator for the constitution test set (Phase 1). Runs the real check with AI_MODE=recorded.

caught           planted faults Greenlight flagged (missing, changed, in conflict, or needs a human look)
missed           planted faults shown as present (a wrong green), plus an unreadable file not reported as such
wrongly_flagged  clauses the answer key says are fine but Greenlight shows red, plus not-applicable mismatches
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from app.services.recognition import check_upload

TEXTS = Path(__file__).resolve().parents[2] / "data" / "eval" / "constitutions"
RED_STATES = {"missing", "weak", "contradicts"}


def evaluate_case(case: dict[str, Any], ruleset: Any) -> dict[str, Any]:
    text = (TEXTS / case["file"]).read_text(encoding="utf-8")
    report, _ = check_upload(ruleset, dict(case["club"]), text=text)
    expected = case["expected"]
    detail: dict[str, Any] = {"id": case["id"], "caught": [], "missed": [], "wrongly_flagged": [], "state_differs": []}
    if not expected["readable"]:
        if report.readable or report.overall is not None:
            detail["missed"].append("unreadable file was checked as if readable")
        return detail
    if not report.readable:
        detail["missed"].extend(f["rule_id"] for f in expected["findings"])
        return detail
    states = {result.rule_id: result.state for result in report.clauses}
    faults = {finding["rule_id"]: finding["state"] for finding in expected["findings"]}
    for rule_id, state in faults.items():
        got = states.get(rule_id, "present")
        if got in ("present", "not_applicable"):
            detail["missed"].append(rule_id)
        else:
            detail["caught"].append(rule_id)
            if got != state:
                detail["state_differs"].append(f"{rule_id}: expected {state}, shown {got}")
    for rule_id, state in states.items():
        if rule_id not in faults and state in RED_STATES:
            detail["wrongly_flagged"].append(rule_id)
    shown_na = sorted(rule_id for rule_id, state in states.items() if state == "not_applicable")
    if shown_na != sorted(expected["not_applicable"]):
        detail["wrongly_flagged"].append(f"not applicable: shown {shown_na}, expected {sorted(expected['not_applicable'])}")
    return detail


def evaluate(data: dict[str, Any], ruleset: Any) -> dict[str, Any]:
    details = [evaluate_case(case, ruleset) for case in data["cases"]]
    caught = sum(len(d["caught"]) for d in details)
    missed = sum(len(d["missed"]) for d in details)
    wrong = sum(len(d["wrongly_flagged"]) for d in details)
    differs = sum(len(d["state_differs"]) for d in details)
    seeded = sum(case["expected"]["seeded_faults"] for case in data["cases"])
    return {
        "caught": caught,
        "missed": missed,
        "wrongly_flagged": wrong,
        "details": details,
        "notes": f"{caught}/{seeded} planted faults found; {differs} found with a different state than the answer key",
    }
