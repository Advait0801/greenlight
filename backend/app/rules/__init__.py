"""The rule table: rules/*.json, their source snapshots and the academic calendar.

This package is pure Python and must never import the AI client (`app.ai`).
"""

from __future__ import annotations

from functools import lru_cache

from app.config import get_settings
from app.rules.calendar import AcademicCalendar, CalendarLoadError, load_calendar
from app.rules.citations import citation_for
from app.rules.loader import RuleLoadError, RuleSet, load_rules
from app.rules.schema import Rule


@lru_cache
def get_ruleset() -> RuleSet:
    """The loaded rule table. Raises RuleLoadError if any rule is invalid."""
    return load_rules(get_settings().rules_dir)


@lru_cache
def get_calendar() -> AcademicCalendar:
    return load_calendar(get_settings().rules_dir)


__all__ = [
    "AcademicCalendar",
    "CalendarLoadError",
    "Rule",
    "RuleLoadError",
    "RuleSet",
    "citation_for",
    "get_calendar",
    "get_ruleset",
    "load_calendar",
    "load_rules",
]
