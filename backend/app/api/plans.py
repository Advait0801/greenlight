"""Year plan routes: the plan (code only), its calendar file, the demo club's plan, and reading a pasted list of
events into rows the officer confirms (AI, through the event packet's reading step).

The plan is worked out again from the whole request on every call and nothing derived is stored, so editing or
deleting an event can never leave a stale date, sum or problem behind. Nothing here submits anything.
"""

from __future__ import annotations

import re
from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.api.deps import require_calendar, require_ruleset
from app.api.events import today_at_usc
from app.config import REPO_ROOT, get_settings
from app.db import get_session
from app.jsonutil import loads_strict
from app.rules import AcademicCalendar, RuleSet
from app.schemas.plans import PlanEvent, YearPlanReport, YearPlanRequest
from app.services.event_intake import MAX_SENTENCE_CHARS, IntakeError, parse_sentence
from app.services.ics import plan_to_ics
from app.services.rule_engine import UnknownAttribute
from app.services.usg_deadline_table import DeadlineTableError
from app.services.year_planner import plan_year

router = APIRouter(prefix="/plans", tags=["plans"])
DEMO_FILE = REPO_ROOT / "data" / "demo" / "club.json"
MAX_READ_LINES = 20


def _as_of(body: YearPlanRequest) -> date:
    today = today_at_usc()
    if body.as_of is None:
        return today
    if abs((body.as_of - today).days) > 3 * 366:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                            detail={"message": "as_of must be within three years of today"})
    return body.as_of


def _plan(body: YearPlanRequest, ruleset: RuleSet, calendar: AcademicCalendar) -> YearPlanReport:
    try:
        return plan_year(body, ruleset, calendar, _as_of(body), get_settings().rules_dir / "sources")
    except UnknownAttribute as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail={"message": str(exc)}) from exc
    except (DeadlineTableError, OSError) as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                            detail={"message": "Greenlight's copy of USG's deadline table could not be read."}) from exc


@router.post("/plan")
def plan(body: YearPlanRequest, ruleset: RuleSet = Depends(require_ruleset),
         calendar: AcademicCalendar = Depends(require_calendar)) -> YearPlanReport:
    """The whole year plan, worked out from scratch: calendar, budget, funding strategy, problems, this week."""
    return _plan(body, ruleset, calendar)


@router.post("/calendar.ics")
def plan_calendar(body: YearPlanRequest, ruleset: RuleSet = Depends(require_ruleset),
                  calendar: AcademicCalendar = Depends(require_calendar)) -> Response:
    text = plan_to_ics(_plan(body, ruleset, calendar))
    return Response(content=text, media_type="text/calendar; charset=utf-8",
                    headers={"Content-Disposition": 'attachment; filename="greenlight-year-plan.ics"'})


def _slug(name: str, taken: set[str]) -> str:
    base = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")[:50] or "event"
    key, n = base, 2
    while key in taken:
        key, n = f"{base}-{n}", n + 1
    taken.add(key)
    return key


@router.get("/demo")
def demo_plan() -> YearPlanRequest:
    """The demo club's plan (data/demo/club.json, PROJECT_CONTEXT section 11), as a request the page can edit."""
    try:
        demo = loads_strict(DEMO_FILE.read_text(encoding="utf-8"))
        club, plan_data = demo["club"], demo["year_plan"]
        taken: set[str] = set()
        events = []
        for item in demo["events"]:
            attrs = item.get("attributes", {})
            events.append(PlanEvent(
                key=_slug(item["name"], taken), name=item["name"], event_date=item["event_date"], end_date=item.get("end_date"),
                venue=attrs.get("venue"), headcount=attrs.get("headcount"), attributes=list(attrs.get("flags", [])),
                estimated_cost_cents=item["estimated_cost_cents"], usg_request_cents=attrs.get("usg_request_cents", 0)))
        return YearPlanRequest(
            club_name=club["name"], mission=club.get("purpose", ""), level=club.get("level"),
            money_on_hand_cents=plan_data["money_on_hand_cents"], expected_income_cents=plan_data["expected_income_cents"],
            usg_received_this_year_cents=plan_data.get("usg_received_this_year_cents"),
            unavailable_dates=plan_data.get("unavailable_dates", []), events=events)
    except Exception as exc:  # noqa: BLE001 - any problem with the demo file is the same answer to the browser
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                            detail={"message": "The demo plan could not be loaded."}) from exc


class ReadEventsRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    # One event per line, in the officer's own words.
    text: str = Field(min_length=1, max_length=MAX_READ_LINES * MAX_SENTENCE_CHARS)


@router.post("/read-events")
def read_events(body: ReadEventsRequest, ruleset: RuleSet = Depends(require_ruleset),
                session: Session = Depends(get_session)) -> dict[str, Any]:
    """Turn a pasted list (one event per line) into event rows for the officer to check. The model only reads each
    line, through the event packet's reading step; it never invents an event, a cost or a date. Unsure details come
    back as questions; a line it could not read comes back with a message so the officer can fill it in by hand."""
    lines = [line.strip(" \t-*•") for line in body.text.splitlines()]
    lines = [line for line in lines if line]
    if not lines:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail={"message": "The list is empty."})
    if len(lines) > MAX_READ_LINES:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                            detail={"message": f"Paste at most {MAX_READ_LINES} events at a time (one per line)."})
    rows: list[dict[str, Any]] = []
    for number, line in enumerate(lines, start=1):
        try:
            parsed = parse_sentence(line, ruleset=ruleset)
        except IntakeError as exc:
            rows.append({"line": number, "text": line, "facts": None, "notes": [], "error": str(exc),
                         "had_instructions": False})
            continue
        parsed.log(session)
        rows.append({"line": number, "text": line, "facts": parsed.facts.model_dump(mode="json"), "notes": parsed.notes,
                     "error": None, "had_instructions": parsed.sentence_had_instructions})
    session.commit()
    return {"rows": rows}


__all__ = ["router"]
