"""Phase 0, iteration 4 (break): an academic calendar that is missing a term, or that claims a
definition no source gives, loads silently.

PLAN.md Phase 0 asks for an academic calendar for Spring 2027. The loader checks every date it is
given against the Registrar's text, but not that the terms the plan and the rules depend on are
there, and it lets the academic-week definition be marked 'read' with no definition and no
matching rule.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from app.rules import CalendarLoadError, calendar_rule_problems, load_calendar, load_rules


def _edit_calendar(rules_dir: Path, change: Callable[[dict[str, Any]], None]) -> None:
    path = rules_dir / "calendar.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    change(data)
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


def test_calendar_without_spring_2027_is_refused(rules_copy: Path) -> None:
    """Delete the Spring 2027 term (classes, spring recess, study days, finals). The file loads, the
    app reports the calendar as confirmed, and May 5, 2027 (finals) is no longer a finals day, so a
    later "no USG funding during finals" check has nothing to block on."""

    def drop_spring(data: dict[str, Any]) -> None:
        data["terms"] = [term for term in data["terms"] if term["id"] != "spring-2027"]

    _edit_calendar(rules_copy, drop_spring)
    with pytest.raises(CalendarLoadError) as caught:
        load_calendar(rules_copy)
    assert any("spring" in problem.lower() for problem in caught.value.problems), caught.value.problems


def test_academic_weeks_marked_read_without_a_definition_is_refused(rules_copy: Path) -> None:
    """`academic_weeks: {"definition": null, "verified": "read"}` claims a confirmed definition that does
    not exist and disagrees with rule usg-academic-week-definition (unverified). The same mismatch for
    business days is caught (calendar_rule_problems); for academic weeks nothing notices."""
    _edit_calendar(rules_copy, lambda d: d["academic_weeks"].update(verified="read"))
    try:
        calendar = load_calendar(rules_copy)
    except CalendarLoadError:
        return
    problems = calendar_rule_problems(load_rules(rules_copy), calendar)
    assert any("academic" in problem for problem in problems), (
        "a calendar whose academic-week definition is marked 'read' but is null, beside an unverified "
        f"usg-academic-week-definition rule, loads with no problem: {problems}"
    )
