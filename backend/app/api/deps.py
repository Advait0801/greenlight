from __future__ import annotations

from fastapi import HTTPException, status

from app.config import REPO_ROOT, get_settings
from app.rules import AcademicCalendar, CalendarLoadError, RuleLoadError, RuleSet, get_calendar, get_ruleset


def public_problems(problems: list[str]) -> list[str]:
    """Problems as shown to a browser: file paths relative to the repository or the rule folder,
    never absolute server paths."""
    prefixes = {str(REPO_ROOT) + "/", str(get_settings().rules_dir.parent) + "/"}
    out = []
    for problem in problems:
        for prefix in sorted(prefixes, key=len, reverse=True):
            problem = problem.replace(prefix, "")
        out.append(problem)
    return out


_public = public_problems


def require_ruleset() -> RuleSet:
    """Dependency for any route that checks something against the rules.

    If the rule table does not load, checks are refused with a clear message instead of being
    run against a partial table.
    """
    try:
        return get_ruleset()
    except RuleLoadError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"message": "The rule table did not load, so no checks can run.", "problems": _public(exc.problems)},
        ) from exc


def require_calendar() -> AcademicCalendar:
    try:
        return get_calendar()
    except CalendarLoadError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"message": "The academic calendar did not load.", "problems": _public(exc.problems)},
        ) from exc
