from __future__ import annotations

from fastapi import HTTPException, status

from app.rules import AcademicCalendar, CalendarLoadError, RuleLoadError, RuleSet, get_calendar, get_ruleset


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
            detail={"message": "The rule table did not load, so no checks can run.", "problems": exc.problems},
        ) from exc


def require_calendar() -> AcademicCalendar:
    try:
        return get_calendar()
    except CalendarLoadError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"message": "The academic calendar did not load.", "problems": exc.problems},
        ) from exc
