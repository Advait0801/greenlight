"""The deadline calculator: dates worked back (or forward) from an anchor date, in plain Python.

This is the only place in the app that turns a rule's lead time into a date. The rule engine, the
test-set validator and (later) the year planner all call it. It never imports the AI client
(tests/unit/test_architecture.py).

Units:
  days, weeks         calendar days
  months              same day of the month, or the month's last day when that month is shorter
                      (May 31 minus 3 months is February 28)
  business_days       every Monday to Friday counts, holidays and recess days included, which gives the
                      earliest date the office could mean, so a deadline is never shown late
                      (rules/calendar.json business_days; unverified, so shown yellow)
  hours               no date: the clock time of the anchor is not known
  academic_weeks      no date: no source defines an academic week. USG's deadline table answers it, but
                      Greenlight's copy is unconfirmed, and rule usg-academic-week-definition says to give
                      no date until a person confirms it ("check with USG").
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Literal

from app.rules.loader import DAYS_PER_UNIT
from app.rules.schema import Rule

COUNTED_UNITS = ("days", "weeks", "months", "business_days")
Direction = Literal["before", "after"]


def _add_months(day: date, months: int) -> date:
    month_index = day.year * 12 + (day.month - 1) + months
    year, month = divmod(month_index, 12)
    month += 1
    next_month = date(year + (month == 12), month % 12 + 1, 1)
    last = (next_month - timedelta(days=1)).day
    return date(year, month, min(day.day, last))


def _add_business_days(day: date, count: int, step: int) -> date:
    while count > 0:
        day += timedelta(days=step)
        if day.weekday() < 5:
            count -= 1
    return day


def shift(day: date, offset: int, unit: str, direction: Direction) -> date | None:
    """`offset` `unit`s before or after `day`, or None when the unit cannot be turned into a date."""
    if offset < 0:
        raise ValueError("offset must not be negative")
    sign = -1 if direction == "before" else 1
    if unit == "days":
        return day + timedelta(days=sign * offset)
    if unit == "weeks":
        return day + timedelta(weeks=sign * offset)
    if unit == "months":
        return _add_months(day, sign * offset)
    if unit == "business_days":
        return _add_business_days(day, offset, sign)
    return None


def anchor_date(rule: Rule, *, start: date | None, end: date | None) -> date | None:
    """The date a deadline rule counts from, when the event gives it. Other anchors (the first payment to a
    vendor, a notification, the day travel starts) are not known from an event description."""
    anchor = rule.anchor or "event_date"
    if anchor == "event_date":
        return start
    if anchor == "event_end_date":
        return end or start
    return None


def due_date(rule: Rule, *, start: date | None, end: date | None = None) -> date | None:
    """The due date of a deadline rule for an event, or None when it cannot be computed."""
    if rule.kind != "deadline" or rule.offset is None or rule.unit is None or rule.direction is None:
        return None
    base = anchor_date(rule, start=start, end=end)
    if base is None:
        return None
    return shift(base, rule.offset, rule.unit, rule.direction)


def latest_start_meeting(rule: Rule, as_of: date) -> date | None:
    """For a 'before' deadline counted from the event's first day: the earliest event date whose deadline is
    on or after `as_of` (the fallback 'move the event to on or after ...'). None when it cannot be computed."""
    if rule.kind != "deadline" or rule.direction != "before" or (rule.anchor or "event_date") != "event_date":
        return None
    if rule.offset is None or rule.unit not in COUNTED_UNITS:
        return None
    # The smallest event date whose deadline is on or after as_of: start at as_of (a deadline is never after its
    # event) and step one day at a time. Bounded: the offset is at most 730 units (rules/schema.py).
    candidate = as_of
    while (due := shift(candidate, rule.offset, rule.unit, "before")) is not None and due < as_of:
        candidate += timedelta(days=1)
    return candidate


def stricter_of(first: Rule, second: Rule, due_first: date | None, due_second: date | None) -> str | None:
    """Which of two disagreeing deadline rules is stricter, or None when it cannot be told.

    The earlier date is stricter (more lead time before an event, less time allowed after it). Without dates,
    the larger lead time is stricter for 'before' deadlines when its anchor is not later than the other's (the
    first payment to a vendor is never after the event), and for 'after' deadlines the shorter time is
    stricter, judged by the longest it could last (2 business days can last 4 calendar days; 48 hours cannot).
    """
    if due_first and due_second:
        if due_first == due_second:
            return None
        return first.id if due_first < due_second else second.id
    if first.kind != "deadline" or second.kind != "deadline" or first.direction != second.direction:
        return None
    if first.offset is None or second.offset is None or first.unit is None or second.unit is None:
        return None
    if first.direction == "before":
        lead_first = first.offset * DAYS_PER_UNIT[first.unit]
        lead_second = second.offset * DAYS_PER_UNIT[second.unit]
        if lead_first == lead_second:
            return None
        longer, shorter = (first, second) if lead_first > lead_second else (second, first)
        if _anchor_rank(longer) <= _anchor_rank(shorter):
            return longer.id
        return None
    if (first.anchor or "event_date") != (second.anchor or "event_date"):
        return None
    span_first, span_second = _longest_span(first), _longest_span(second)
    if span_first == span_second:
        return None
    return first.id if span_first < span_second else second.id


def _anchor_rank(rule: Rule) -> int:
    """Anchors in the order they fall: the first payment comes before (or on) the event or the day travel starts."""
    return {"initial_payment_due_date": 0, "event_date": 1, "travel_date": 1}.get(rule.anchor or "event_date", 2)


def _longest_span(rule: Rule) -> float:
    """The longest a time allowed 'after' an anchor could last, in days."""
    offset = rule.offset or 0
    if rule.unit == "business_days":
        return offset + 2 * ((offset + 4) // 5) + 0.999  # weekends in between, and the whole last day
    if rule.unit == "hours":
        return offset / 24
    return offset * DAYS_PER_UNIT[rule.unit or "days"] + 0.999
