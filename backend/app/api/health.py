from __future__ import annotations

from collections import Counter
from typing import Any

from fastapi import APIRouter, Response, status
from sqlalchemy import text

from app.api.deps import public_problems as _public
from app.config import get_settings
from app.db import get_engine
from app.rules import CalendarLoadError, RuleLoadError, calendar_rule_problems, get_calendar, get_ruleset
from app.schemas.common import PRECHECK_NOTICE

router = APIRouter(tags=["health"])


def _rules_status() -> dict[str, Any]:
    try:
        ruleset = get_ruleset()
    except RuleLoadError as exc:
        return {"loaded": False, "count": 0, "problems": _public(exc.problems)}
    try:
        problems = calendar_rule_problems(ruleset, get_calendar())
    except CalendarLoadError:
        problems = []  # reported under "calendar"
    return {
        "loaded": True,
        "count": len(ruleset),
        "by_domain": dict(sorted(Counter(rule.domain for rule in ruleset).items())),
        "by_verification": dict(sorted(Counter(rule.verified for rule in ruleset).items())),
        "shown_yellow_until_verified": sum(1 for rule in ruleset if not ruleset.is_certain(rule.id)),
        "problems": _public(problems),
    }


def _calendar_status() -> dict[str, Any]:
    try:
        calendar = get_calendar()
    except CalendarLoadError as exc:
        return {"loaded": False, "problems": _public(exc.problems)}
    return {
        "loaded": True,
        "verified": calendar.verified,
        "verification_note": calendar.verification_note,
        "terms": [term.name for term in calendar.terms],
        "problems": [],
    }


def _database_status() -> str:
    try:
        with get_engine().connect() as connection:
            connection.execute(text("SELECT 1"))
    except Exception as exc:  # noqa: BLE001 - report any database failure as text
        return f"error: {type(exc).__name__}"
    return "ok"


@router.get("/health")
def health(response: Response) -> dict[str, Any]:
    """Is the app running, and did the rule table, calendar and database load?

    Answers 200 when everything loaded and 503 (same body) when something did not.
    """
    rules = _rules_status()
    calendar = _calendar_status()
    database = _database_status()
    healthy = rules["loaded"] and not rules["problems"] and calendar["loaded"] and database == "ok"
    if not healthy:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return {
        "status": "ok" if healthy else "degraded",
        "app": "greenlight",
        "notice": PRECHECK_NOTICE,
        "ai_mode": get_settings().ai_mode.value,
        "database": database,
        "rules": rules,
        "calendar": calendar,
    }
