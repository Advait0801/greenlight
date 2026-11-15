"""The rule table: rules/*.json, their source snapshots and the academic calendar.

This package is pure Python and must never import the AI client (`app.ai`).
"""

from __future__ import annotations

from functools import lru_cache

from app.config import get_settings
from app.rules.calendar import AcademicCalendar, CalendarLoadError, load_calendar
from app.rules.citations import citation_for, finding_for
from app.rules.loader import RuleLoadError, RuleSet, load_rules
from app.rules.schema import Rule


@lru_cache
def get_ruleset() -> RuleSet:
    """The loaded rule table. Raises RuleLoadError if any rule is invalid."""
    return load_rules(get_settings().rules_dir)


@lru_cache
def get_calendar() -> AcademicCalendar:
    return load_calendar(get_settings().rules_dir)


def calendar_rule_problems(ruleset: RuleSet, calendar: AcademicCalendar) -> list[str]:
    """The rule table and the calendar must agree on what is verified: the calendar pointer rule
    with the calendar, and the business-day rule with the calendar's business-day assumption."""
    problems = []
    pairs = (
        (calendar.id, calendar.verified, "rules/calendar.json"),
        ("usc-business-days-definition", calendar.business_days.verified, "rules/calendar.json business_days"),
        ("usg-academic-week-definition", calendar.academic_weeks.verified, "rules/calendar.json academic_weeks"),
    )
    for rule_id, verified, where in pairs:
        rule = ruleset.rules.get(rule_id)
        if rule is None:
            problems.append(f"no rule '{rule_id}' for {where}")
        elif rule.verified != verified:
            problems.append(f"rule '{rule_id}' is marked '{rule.verified}' but {where} is marked '{verified}'; they must agree")
    return problems


__all__ = [
    "AcademicCalendar",
    "CalendarLoadError",
    "Rule",
    "RuleLoadError",
    "RuleSet",
    "calendar_rule_problems",
    "citation_for",
    "finding_for",
    "get_calendar",
    "get_ruleset",
    "load_calendar",
    "load_rules",
]
