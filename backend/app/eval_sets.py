"""Load and validate the test sets in data/eval/ (the accuracy test sets).

Each set is checked against its JSON Schema (data/eval/schemas/) and then for consistency:
case ids unique, rule ids that exist in the rule table, sums that add up, files that exist.
Any problem raises EvalSetError listing every problem found.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from app.config import REPO_ROOT
from app.jsonutil import StrictJSONError, loads_strict
from app.rules.loader import RuleSet

EVAL_DIR = REPO_ROOT / "data" / "eval"
SETS: dict[str, str] = {
    "events": "events/cases.json",
    "budgets": "budgets/cases.json",
    "constitutions": "constitutions/cases.json",
    "year_plans": "year_plans/cases.json",
}


class EvalSetError(Exception):
    def __init__(self, set_name: str, problems: list[str]) -> None:
        self.set_name = set_name
        self.problems = problems
        lines = "\n".join(f"  - {problem}" for problem in problems)
        super().__init__(f"test set '{set_name}' is invalid ({len(problems)} problem(s)):\n{lines}")


def _schema(eval_dir: Path, name: str) -> dict[str, Any]:
    schema: dict[str, Any] = json.loads((eval_dir / "schemas" / f"{name}.schema.json").read_text(encoding="utf-8"))
    return schema


def _iso(value: Any) -> date | None:
    if not isinstance(value, str):
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _check_dates(node: Any, path: str, problems: list[str]) -> None:
    """Every value under a key ending in 'date', 'due' or 'as_of' must be a real calendar date."""
    if isinstance(node, dict):
        for key, value in node.items():
            here = f"{path}.{key}"
            if (key.endswith("date") or key in ("due", "as_of", "first_registered")) and isinstance(value, str):
                if _iso(value) is None:
                    problems.append(f"{here}: '{value}' is not a real date")
            if key.endswith("dates") and isinstance(value, list):
                for index, item in enumerate(value):
                    if isinstance(item, str) and _iso(item) is None:
                        problems.append(f"{here}[{index}]: '{item}' is not a real date")
            start, end = _iso(node.get("event_date")), _iso(node.get("end_date"))
            if key == "end_date" and start and end and end < start:
                problems.append(f"{path}: end_date is before event_date")
            _check_dates(value, here, problems)
    elif isinstance(node, list):
        for index, value in enumerate(node):
            _check_dates(value, f"{path}[{index}]", problems)


def _rule_refs(node: Any, path: str, out: list[tuple[str, str]]) -> None:
    if isinstance(node, dict):
        for key, value in node.items():
            here = f"{path}.{key}"
            if key in ("rule_id", "contradicted_by", "applied", "expected_fund") and isinstance(value, str):
                out.append((here, value))
            elif key in ("rules", "not_applicable", "acceptable_funds") and isinstance(value, list):
                out.extend((f"{here}[{i}]", item) for i, item in enumerate(value) if isinstance(item, str))
            else:
                _rule_refs(value, here, out)
    elif isinstance(node, list):
        for index, value in enumerate(node):
            _rule_refs(value, f"{path}[{index}]", out)


def _check_events(data: dict[str, Any], ruleset: RuleSet | None, problems: list[str]) -> None:
    vocabulary = {name for group in (ruleset.vocabulary.values() if ruleset else []) for name in group}
    for case in data["cases"]:
        cid, expected = case["id"], case["expected"]
        if vocabulary:
            unknown = [a for a in expected["attributes"] if a not in vocabulary]
            if unknown:
                problems.append(f"{cid}: attributes not in rules/vocabulary.json: {', '.join(unknown)}")
        ids = [o["rule_id"] for o in expected["obligations"]]
        if len(ids) != len(set(ids)):
            problems.append(f"{cid}: an obligation is listed twice")
        if expected["event_date"] is None and "event_date" not in expected["needs_officer_input"]:
            problems.append(f"{cid}: no event_date, so needs_officer_input must include 'event_date'")
        for o in expected["obligations"]:
            if o["status"] == "blocked" and not o["violated"]:
                problems.append(f"{cid}: {o['rule_id']} is blocked but not marked violated")


def _check_budgets(data: dict[str, Any], problems: list[str]) -> None:
    for case in data["cases"]:
        cid, lines, expected = case["id"], case["lines"], case["expected"]
        numbers = [line["line"] for line in lines]
        if numbers != list(range(1, len(lines) + 1)):
            problems.append(f"{cid}: line numbers must run 1..{len(lines)}")
        for line in lines:
            if line["amount_cents"] != line["quantity"] * line["unit_price_cents"]:
                problems.append(f"{cid} line {line['line']}: amount_cents is not quantity x unit_price_cents")
        total = sum(line["amount_cents"] for line in lines)
        if expected["total_cents"] != total:
            problems.append(f"{cid}: total_cents {expected['total_cents']} does not equal the sum of lines {total}")
        food = sum(line["amount_cents"] for line in lines if line["category"] == "food")
        attendance = case["event"]["expected_attendance"]
        fpp = expected["food_per_person_cents"]
        if food and attendance:
            if fpp is None or fpp * attendance != food:
                problems.append(f"{cid}: food_per_person_cents does not equal food total / expected attendance")
        elif fpp is not None:
            problems.append(f"{cid}: food_per_person_cents must be null without food or attendance")
        if [entry["line"] for entry in expected["lines"]] != numbers:
            problems.append(f"{cid}: expected.lines must give a verdict for every line, in order")
        reds = any(entry["verdict"] == "red" for entry in expected["lines"]) or any(
            finding["verdict"] == "red" for finding in expected["application"]
        )
        if expected["draft_allowed"] == reds:
            problems.append(f"{cid}: draft_allowed must be false exactly when a red finding remains")
        fund = expected["expected_fund"]
        if fund is not None and fund not in expected["acceptable_funds"]:
            problems.append(f"{cid}: expected_fund must be one of acceptable_funds")


def _check_constitutions(data: dict[str, Any], eval_dir: Path, ruleset: RuleSet | None, problems: list[str]) -> None:
    clause_ids = {rule.id for rule in ruleset if rule.kind == "clause"} if ruleset else set()
    base = eval_dir / "constitutions"
    for case in data["cases"]:
        cid, expected = case["id"], case["expected"]
        path = (base / case["file"]).resolve()
        if base.resolve() not in path.parents:
            problems.append(f"{cid}: file path escapes data/eval/constitutions")
        elif not path.is_file():
            problems.append(f"{cid}: file {case['file']} not found")
        elif not path.read_text(encoding="utf-8").strip():
            problems.append(f"{cid}: file {case['file']} is empty")
        if expected["seeded_faults"] != len(expected["findings"]):
            problems.append(f"{cid}: seeded_faults must equal the number of findings")
        listed = [f["rule_id"] for f in expected["findings"]] + expected["not_applicable"]
        if len(listed) != len(set(listed)):
            problems.append(f"{cid}: a clause is listed twice across findings and not_applicable")
        if clause_ids:
            for rule_id in listed:
                if rule_id not in clause_ids:
                    problems.append(f"{cid}: {rule_id} is not a constitution clause rule")


def _check_year_plans(data: dict[str, Any], problems: list[str]) -> None:
    for case in data["cases"]:
        cid = case["id"]
        keys = [event["key"] for event in case["events"]]
        if len(keys) != len(set(keys)):
            problems.append(f"{cid}: event keys must be unique")
        known = set(keys)
        for entry in case["expected"]["calendar"]:
            if entry["event"] not in known:
                problems.append(f"{cid}: calendar entry names unknown event '{entry['event']}'")
        for problem in case["expected"]["problems"]:
            for key in problem["events"]:
                if key not in known:
                    problems.append(f"{cid}: problem names unknown event '{key}'")
        plan, budget = case["plan"], case["expected"]["budget"]
        total = sum(event["estimated_cost_cents"] for event in case["events"])
        available = plan["money_on_hand_cents"] + plan["expected_income_cents"]
        usg = sum(event["usg_request_cents"] for event in case["events"])
        checks = {
            "total_cost_cents": total,
            "funds_available_cents": available,
            "gap_before_usg_cents": max(0, total - available),
            "usg_requested_cents": usg,
        }
        for key, value in checks.items():
            if budget[key] != value:
                problems.append(f"{cid}: budget.{key} is {budget[key]}, but the plan gives {value}")


def validate_set(name: str, data: Any, *, eval_dir: Path = EVAL_DIR, ruleset: RuleSet | None = None) -> list[str]:
    """Every problem with one test set, as plain-language lines. Empty means valid."""
    if name not in SETS:
        return [f"unknown test set '{name}'; known: {', '.join(SETS)}"]
    validator = Draft202012Validator(_schema(eval_dir, name))
    problems = [
        f"{'/'.join(str(p) for p in error.absolute_path) or '(top level)'}: {error.message}"
        for error in sorted(validator.iter_errors(data), key=lambda e: list(e.absolute_path))
    ]
    if problems:
        return problems  # consistency checks assume the shape is right
    ids = [case["id"] for case in data["cases"]]
    if len(ids) != len(set(ids)):
        problems.append("case ids must be unique")
    _check_dates(data, name, problems)
    if ruleset is not None:
        refs: list[tuple[str, str]] = []
        _rule_refs(data["cases"], "cases", refs)
        problems.extend(f"{where}: rule '{rule_id}' is not in the rule table" for where, rule_id in refs if rule_id not in ruleset)
    if name == "events":
        _check_events(data, ruleset, problems)
    elif name == "budgets":
        _check_budgets(data, problems)
    elif name == "constitutions":
        _check_constitutions(data, eval_dir, ruleset, problems)
    elif name == "year_plans":
        _check_year_plans(data, problems)
    return problems


def load_set(name: str, *, eval_dir: Path = EVAL_DIR, ruleset: RuleSet | None = None) -> dict[str, Any]:
    """Read and validate one test set. Raises EvalSetError with every problem found."""
    if name not in SETS:
        raise EvalSetError(name, [f"unknown test set; known: {', '.join(SETS)}"])
    path = eval_dir / SETS[name]
    try:
        data = loads_strict(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise EvalSetError(name, [f"{path} not found"]) from exc
    except json.JSONDecodeError as exc:
        raise EvalSetError(name, [f"{path.name}: not valid JSON (line {exc.lineno}, column {exc.colno}: {exc.msg})"]) from exc
    except StrictJSONError as exc:
        raise EvalSetError(name, [f"{path.name}: {exc}"]) from exc
    problems = validate_set(name, data, eval_dir=eval_dir, ruleset=ruleset)
    if problems:
        raise EvalSetError(name, problems)
    result: dict[str, Any] = data
    return result
