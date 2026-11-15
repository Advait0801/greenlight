"""Handover packet (PROJECT_CONTEXT 4G): one editable packet per officer role, built by code from the club's saved
history, and a starting plan for next year.

The saved history is what the club keeps: its year plan (saved in the officer's browser, private to the club) and the
applications it chose to send to the USG screen, read back with the club's own token, with any reason a USG reviewer
approved. Every date, figure and verdict comes from the year planner (Phase 4) and the stored money check reports;
nothing here calls the model. The officer edits each packet before using it.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from pydantic import BaseModel

from app.models import SentApplication
from app.rules import AcademicCalendar, RuleSet
from app.schemas.common import PRECHECK_NOTICE
from app.schemas.events import LATEST
from app.schemas.plans import YearPlanReport, YearPlanRequest
from app.services.money_check import money
from app.services.year_planner import plan_year

MAX_UPCOMING = 15
ROLES = ("President", "Treasurer", "Events lead")


class RolePacket(BaseModel):
    role: str
    text: str


class HandoverPacket(BaseModel):
    as_of: date
    club_name: str
    packets: list[RolePacket]
    next_year_plan: YearPlanRequest
    notes: list[str]
    notice: str


def _next_year(day: date | None) -> date | None:
    """The same weekday one year on (52 weeks later), so a Friday event stays a Friday."""
    if day is None:
        return None
    moved = day + timedelta(weeks=52)
    return moved if moved <= LATEST else None


def seed_next_year(plan: YearPlanRequest) -> YearPlanRequest:
    events = [event.model_copy(update={"event_date": _next_year(event.event_date),
                                       "end_date": _next_year(event.end_date) if _next_year(event.event_date) else None})
              for event in plan.events]
    return YearPlanRequest(club_name=plan.club_name, mission=plan.mission, level=plan.level, money_on_hand_cents=0,
                           expected_income_cents=0, usg_received_this_year_cents=None, unavailable_dates=[], events=events)


def _event_lines(report: YearPlanReport, as_of: date, past: bool) -> list[str]:
    out = []
    for e in report.events:
        is_past = e.event_date is not None and (e.end_date or e.event_date) < as_of
        if is_past != past:
            continue
        when = e.event_date.isoformat() if e.event_date else "no date"
        out.append(f"- {e.name} ({when}): estimated cost {money(e.budget.cost_cents)}; {e.verdict_label.lower()}.")
    return out or ["- None."]


def _applications(rows: list[SentApplication]) -> tuple[list[str], list[str], list[str]]:
    vendors: dict[str, set[str]] = {}
    sent: list[str] = []
    denied: list[str] = []
    for row in rows:
        report: dict[str, Any] = row.report
        total = money(int(report.get("totals", {}).get("total_cents", 0)))
        sent.append(f"- {row.event_name} (reference {row.reference}): {total} checked; Greenlight's pre-check said "
                    f"\"{report.get('verdict_label', report.get('verdict'))}\"; {'withdrawn' if row.status == 'withdrawn' else 'sent to USG'}.")
        for line in report.get("lines", []):
            if line.get("vendor"):
                vendors.setdefault(line["vendor"], set()).add(row.event_name)
        if row.denial_status == "approved" and row.denial_approved_text:
            denied.append(f"- {row.event_name}, as approved by {row.denial_approved_by or 'a USG reviewer'}:\n"
                          + "\n".join(f"    {t}" for t in row.denial_approved_text.splitlines()))
    vendor_lines = [f"- {name} (used for {', '.join(sorted(events))})" for name, events in sorted(vendors.items())]
    return sent or ["- None sent."], vendor_lines or ["- None recorded."], denied or ["- None."]


def build_handover(plan: YearPlanRequest, rows: list[SentApplication], ruleset: RuleSet, calendar: AcademicCalendar,
                   as_of: date, sources_dir: Any) -> HandoverPacket:
    report = plan_year(plan.model_copy(update={"as_of": as_of}), ruleset, calendar, as_of, sources_dir)
    club = plan.club_name.strip() or "The club"
    sent, vendors, denied = _applications(rows)
    upcoming = [i for i in report.calendar if i.day >= as_of and i.kind != "event"][:MAX_UPCOMING]
    upcoming_lines = [f"- {i.day.isoformat()}: {i.title} ({i.event_name}){' - check with USG' if i.unconfirmed else ''}"
                      for i in upcoming] or ["- Nothing dated after today."]
    problems = [f"- {p.severity_label}: {p.note}" for p in report.problems if p.severity.value in ("red", "yellow")][:12]
    budget = report.budget
    header = f"{club} handover, prepared {as_of.isoformat()} from the club's saved year plan and the applications it sent."
    president = "\n".join([
        header, "", f"Mission: {plan.mission.strip() or '(not given)'}", "",
        "Events already held:", *_event_lines(report, as_of, past=True), "",
        "Events still ahead:", *_event_lines(report, as_of, past=False), "",
        "Problems the plan flags now:", *(problems or ["- None."]), "",
        "What USG decided not to fund, and why (reasons a USG reviewer approved):", *denied,
    ])
    treasurer = "\n".join([
        header, "",
        f"Total estimated cost: {money(budget.total_cost_cents)}. Money available: {money(budget.funds_available_cents)}. "
        f"Planned from USG: {money(budget.usg_planned_cents)}. Still to find: {money(budget.shortfall_cents)}.", "",
        "Per event (cost / USG planned / club money / shortfall):",
        *[f"- {r.name}: {money(r.cost_cents)} / {money(r.usg_planned_cents)} / {money(r.club_money_cents)} / {money(r.shortfall_cents)}"
          for r in budget.rows], "",
        "Applications sent to the USG screen:", *sent, "",
        "Vendors on those applications:", *vendors, "",
        "What USG decided not to fund, and why:", *denied,
    ])
    events_lead = "\n".join([
        header, "", f"Next dated steps (up to {MAX_UPCOMING}), each from the event's packet:", *upcoming_lines, "",
        "Events still ahead:", *_event_lines(report, as_of, past=False),
    ])
    notes = ["Edit each packet before you hand it over. Figures and dates come from Greenlight's year plan and money checks."]
    if not rows:
        notes.append("No sent application was added, so vendors and USG reasons are empty. Add the reference and token of "
                     "each application your club sent.")
    return HandoverPacket(as_of=as_of, club_name=plan.club_name, notice=PRECHECK_NOTICE, notes=notes,
                          packets=[RolePacket(role=r, text=t) for r, t in zip(ROLES, (president, treasurer, events_lead), strict=True)],
                          next_year_plan=seed_next_year(plan))
