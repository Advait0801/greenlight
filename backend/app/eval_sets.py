"""Load and validate the test sets in data/eval/ (the accuracy test sets).

Each set is checked against its JSON Schema (data/eval/schemas/) and then for consistency:
case ids unique, rule ids that exist in the rule table, sums that add up, files that exist.
Any problem raises EvalSetError listing every problem found.
"""

from __future__ import annotations

import json
from datetime import date, timedelta
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
    path = eval_dir / "schemas" / f"{name}.schema.json"
    try:
        schema: dict[str, Any] = loads_strict(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise EvalSetError(name, [f"schema {path} not found"]) from exc
    except (UnicodeDecodeError, json.JSONDecodeError, StrictJSONError) as exc:
        raise EvalSetError(name, [f"schema {path.name} is not readable JSON ({exc})"]) from exc
    return schema


VERDICT_ORDER = {"green": 0, "yellow": 1, "office_decides": 2, "red": 3}


def _back(day: date, offset: int, unit: str) -> date | None:
    """A 'before' deadline in plain calendar units: the day minus the lead time."""
    if unit == "days":
        return day - timedelta(days=offset)
    if unit == "weeks":
        return day - timedelta(weeks=offset)
    if unit == "months":
        month, year = day.month - offset, day.year
        while month < 1:
            month, year = month + 12, year - 1
        for candidate in range(day.day, 0, -1):
            try:
                return date(year, month, candidate)
            except ValueError:
                continue
    if unit == "business_days":
        # Every Monday to Friday counts, holidays and recess days included (rules/calendar.json business_days):
        # the earliest date the office could mean, so a deadline is never shown late.
        while offset > 0:
            day -= timedelta(days=1)
            if day.weekday() < 5:
                offset -= 1
        return day
    return None


def _expected_status(ruleset: RuleSet, rule_id: str, violated: bool | None) -> set[str]:
    """Statuses that follow from a rule's certainty, severity and kind. `violated` None means unknown."""
    rule = ruleset.get(rule_id)
    if not ruleset.is_certain(rule_id) or rule.severity == "yellow":
        return {"check_with_office"}
    if rule.severity == "office_decides":
        return {"office_decides"}
    plain = "to_do" if rule.kind in ("deadline", "requirement") else "condition"
    if violated is None:
        return {plain, "blocked"}
    return {"blocked"} if violated else {plain}


def _check_obligation(where: str, ruleset: RuleSet, entry: dict[str, Any], start: date | None, as_of: date | None,
                      problems: list[str]) -> None:
    rule = ruleset.get(entry["rule_id"])
    due = _iso(entry.get("due"))
    if rule.kind == "deadline" and rule.direction == "before" and start and rule.unit in ("days", "weeks", "months", "business_days"):
        want = _back(start, rule.offset or 0, rule.unit)
        if due != want:
            problems.append(f"{where}: {rule.id} is due {entry.get('due')}, but {rule.offset} {rule.unit} before {start} is {want}")
    if rule.unit == "academic_weeks" and entry.get("due") is not None:
        problems.append(f"{where}: {rule.id} counts academic weeks, which no source defines; its due date must be null")
    allowed = _expected_status(ruleset, rule.id, entry.get("violated"))
    explained = entry.get("note") and entry["status"] == "check_with_office"
    if entry["status"] not in allowed and not explained:
        problems.append(f"{where}: {rule.id} has status '{entry['status']}', but the rule gives {sorted(allowed)}")
    if "past_due" in entry and as_of is not None:
        want_past = bool(due and due < as_of and rule.direction == "before")
        if entry["past_due"] != want_past:
            problems.append(f"{where}: {rule.id} past_due must be {want_past} (due {entry.get('due')}, as of {as_of})")


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


def _check_conflicts(where: str, ruleset: RuleSet, obligations: list[dict[str, Any]], conflicts: list[dict[str, Any]],
                     problems: list[str]) -> None:
    listed = {o["rule_id"]: o for o in obligations}
    named = {frozenset(c["rules"]) for c in conflicts}
    for rule_id in listed:
        for other in ruleset.get(rule_id).conflicts_with or []:
            if other in listed and frozenset((rule_id, other)) not in named:
                problems.append(f"{where}: {rule_id} and {other} disagree in the rule table but the conflict is not listed")
    for conflict in conflicts:
        first, second = conflict["rules"]
        if first not in listed or second not in listed:
            problems.append(f"{where}: conflict {first} / {second} names a rule that is not an obligation of this case")
            continue
        applied = conflict["applied"]
        if applied is not None and applied not in (first, second):
            problems.append(f"{where}: the applied rule {applied} is not one of {first} / {second}")
            continue
        due_a, due_b = _iso(listed[first].get("due")), _iso(listed[second].get("due"))
        rule_a, rule_b = ruleset.get(first), ruleset.get(second)
        stricter = None
        if due_a and due_b and due_a != due_b:
            stricter = first if due_a < due_b else second
        elif (rule_a.unit, rule_a.anchor, rule_a.direction) == (rule_b.unit, rule_b.anchor, rule_b.direction) and rule_a.offset != rule_b.offset:
            # Before an anchor, more lead time is stricter; after it, less time is stricter.
            longer = first if (rule_a.offset or 0) > (rule_b.offset or 0) else second
            shorter = second if longer == first else first
            stricter = longer if rule_a.direction == "before" else shorter
        if stricter is not None and applied != stricter:
            problems.append(f"{where}: {stricter} is the stricter of {first} / {second}, so it must be the one applied")


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
        if ruleset is not None and all(o["rule_id"] in ruleset for o in expected["obligations"]):
            for o in expected["obligations"]:
                fact = ruleset.get(o["rule_id"]).params.get("violated_when")
                if fact and o["violated"] != (fact in expected["attributes"]):
                    problems.append(
                        f"{cid}: {o['rule_id']} is broken exactly when '{fact}' is among the attributes; violated must be {fact in expected['attributes']}"
                    )
            start, as_of = _iso(expected["event_date"]), _iso(case["as_of"])
            for o in expected["obligations"]:
                _check_obligation(cid, ruleset, o, start, as_of, problems)
            _check_conflicts(cid, ruleset, expected["obligations"], expected["source_conflicts"], problems)


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
        all_findings = [f for entry in expected["lines"] for f in entry["findings"]] + expected["application"]
        for finding in all_findings:
            reason = finding.get("reason", "rule")
            if reason != "rule" and finding["verdict"] != "yellow":
                problems.append(f"{cid}: a '{reason}' finding is an uncertainty and must be yellow")
            if reason == "rule" and not finding.get("rule_id"):
                problems.append(f"{cid}: a rule finding needs a rule_id (it carries the rule text and source)")
        for entry in expected["lines"]:
            worst = max((f["verdict"] for f in entry["findings"]), key=VERDICT_ORDER.__getitem__, default="green")
            if entry["verdict"] != worst:
                problems.append(f"{cid} line {entry['line']}: verdict {entry['verdict']} but its findings make it {worst}")
        found = {f.get("rule_id") for f in all_findings}
        for seeded in expected["seeded_violations"]:
            if seeded["rule_id"] not in found:
                problems.append(f"{cid}: seeded violation {seeded['rule_id']} ({seeded['where']}) has no matching finding")
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
        else:
            try:
                if not path.read_text(encoding="utf-8").strip():
                    problems.append(f"{cid}: file {case['file']} is empty")
            except UnicodeDecodeError:
                problems.append(f"{cid}: file {case['file']} is not UTF-8 text")
        if expected["seeded_faults"] != len(expected["findings"]):
            problems.append(f"{cid}: seeded_faults must equal the number of findings")
        listed = [f["rule_id"] for f in expected["findings"]] + expected["not_applicable"]
        if len(listed) != len(set(listed)):
            problems.append(f"{cid}: a clause is listed twice across findings and not_applicable")
        if clause_ids:
            for rule_id in listed:
                if rule_id not in clause_ids:
                    problems.append(f"{cid}: {rule_id} is not a constitution clause rule")


def _check_year_plans(data: dict[str, Any], ruleset: RuleSet | None, problems: list[str]) -> None:
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
        if ruleset is None or "usg-yearly-cap" not in ruleset:
            continue
        cap = int(ruleset.get("usg-yearly-cap").params["max_usd_per_year"]) * 100
        over = max(0, plan["usg_received_this_year_cents"] + usg - cap)
        if budget["usg_requested_over_yearly_cap_cents"] != over:
            problems.append(f"{cid}: budget.usg_requested_over_yearly_cap_cents must be {over}")
        if over and not any(p["type"] == "over_yearly_cap" for p in case["expected"]["problems"]):
            problems.append(f"{cid}: the requests exceed the yearly cap by {over} cents but no over_yearly_cap problem is listed")
        events = {event["key"]: event for event in case["events"]}
        for entry in case["expected"]["calendar"]:
            if entry["event"] in events and entry["rule_id"] in ruleset:
                _check_obligation(f"{cid} {entry['event']}", ruleset, {**entry, "violated": None},
                                  _iso(events[entry["event"]]["event_date"]), None, problems)


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
        categories = ruleset.vocabulary.get("line_item_categories", {}) if ruleset else {}
        if categories:
            for case in data["cases"]:
                for line in case["lines"]:
                    if line["category"] not in categories:
                        problems.append(f"{case['id']} line {line['line']}: category '{line['category']}' is not in rules/vocabulary.json")
    elif name == "constitutions":
        _check_constitutions(data, eval_dir, ruleset, problems)
    elif name == "year_plans":
        _check_year_plans(data, ruleset, problems)
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
    except UnicodeDecodeError as exc:
        raise EvalSetError(name, [f"{path.name}: not UTF-8 text ({exc.reason})"]) from exc
    except json.JSONDecodeError as exc:
        raise EvalSetError(name, [f"{path.name}: not valid JSON (line {exc.lineno}, column {exc.colno}: {exc.msg})"]) from exc
    except StrictJSONError as exc:
        raise EvalSetError(name, [f"{path.name}: {exc}"]) from exc
    problems = validate_set(name, data, eval_dir=eval_dir, ruleset=ruleset)
    if problems:
        raise EvalSetError(name, problems)
    result: dict[str, Any] = data
    return result
