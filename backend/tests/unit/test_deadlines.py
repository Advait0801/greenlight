"""The deadline calculator: every date exact (PLAN.md Phase 2: 100%, not 95%)."""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from app.rules import load_rules
from app.rules.schema import Rule
from app.services import deadlines
from tests.conftest import RULES_DIR


@pytest.fixture(scope="module")
def ruleset():  # type: ignore[no-untyped-def]
    return load_rules(RULES_DIR)


def _rule(**changes: object) -> Rule:
    base = {
        "id": "test-deadline", "domain": "events", "kind": "deadline", "title": "Test deadline", "owner_office": "Office",
        "source": "Source", "source_url": "https://example.edu/x", "source_text": "at least some time before the event",
        "effective_date": "2026-10-21", "verified": "read", "severity": "red", "message": "A test deadline.",
        "fix_template": None, "applies_to": "every event", "anchor": "event_date", "offset": 2, "unit": "weeks",
        "direction": "before",
    }
    base.update(changes)
    return Rule.model_validate(base)


@pytest.mark.parametrize(
    ("day", "offset", "unit", "direction", "want"),
    [
        (date(2027, 4, 9), 6, "weeks", "before", date(2027, 2, 26)),
        (date(2027, 4, 9), 21, "days", "before", date(2027, 3, 19)),
        (date(2027, 1, 5), 2, "weeks", "before", date(2026, 12, 22)),  # across the year boundary
        (date(2027, 1, 5), 60, "days", "before", date(2026, 11, 6)),
        (date(2027, 3, 1), 1, "days", "before", date(2027, 2, 28)),  # 2027 is not a leap year
        (date(2028, 3, 1), 1, "days", "before", date(2028, 2, 29)),  # 2028 is
        (date(2027, 4, 17), 3, "months", "before", date(2027, 1, 17)),
        (date(2027, 5, 31), 3, "months", "before", date(2027, 2, 28)),  # shorter month: its last day
        (date(2028, 5, 31), 3, "months", "before", date(2028, 2, 29)),
        (date(2028, 2, 29), 3, "months", "before", date(2027, 11, 29)),
        (date(2027, 1, 31), 3, "months", "before", date(2026, 10, 31)),
        (date(2027, 2, 28), 12, "months", "before", date(2026, 2, 28)),
        (date(2027, 3, 31), 1, "months", "before", date(2027, 2, 28)),
        (date(2027, 3, 16), 3, "business_days", "after", date(2027, 3, 19)),
        (date(2027, 3, 6), 3, "business_days", "after", date(2027, 3, 10)),  # Saturday: Mon, Tue, Wed
        (date(2027, 3, 5), 3, "business_days", "after", date(2027, 3, 10)),  # Friday: Mon, Tue, Wed
        (date(2027, 1, 15), 3, "business_days", "after", date(2027, 1, 20)),  # Monday Jan 18 (a holiday) counts
        (date(2027, 1, 19), 5, "business_days", "before", date(2027, 1, 12)),
        (date(2027, 3, 22), 10, "business_days", "before", date(2027, 3, 8)),
        (date(2026, 12, 30), 3, "business_days", "after", date(2027, 1, 4)),  # across the year boundary
        (date(2027, 4, 9), 0, "days", "before", date(2027, 4, 9)),
    ],
)
def test_shift_is_exact(day: date, offset: int, unit: str, direction: str, want: date) -> None:
    assert deadlines.shift(day, offset, unit, direction) == want  # type: ignore[arg-type]


@pytest.mark.parametrize("unit", ["hours", "academic_weeks"])
def test_units_without_a_date_give_none(unit: str) -> None:
    assert deadlines.shift(date(2027, 4, 9), 6, unit, "before") is None


def test_negative_offsets_are_refused() -> None:
    with pytest.raises(ValueError):
        deadlines.shift(date(2027, 4, 9), -1, "days", "before")


def test_due_dates_use_the_rule_anchor() -> None:
    start, end = date(2027, 3, 4), date(2027, 3, 6)
    assert deadlines.due_date(_rule(), start=start, end=end) == date(2027, 2, 18)
    after = _rule(anchor="event_end_date", offset=3, unit="business_days", direction="after")
    assert deadlines.due_date(after, start=start, end=end) == date(2027, 3, 10)  # Saturday + Mon, Tue, Wed
    assert deadlines.due_date(after, start=start, end=None) == date(2027, 3, 9)  # one-day event: its only day
    assert deadlines.due_date(_rule(anchor="initial_payment_due_date"), start=start, end=end) is None
    assert deadlines.due_date(_rule(anchor="notification_date", unit="hours", offset=48, direction="after"), start=start) is None
    assert deadlines.due_date(_rule(), start=None) is None


def test_every_counted_deadline_in_the_rule_table_matches_a_day_by_day_count(ruleset) -> None:  # type: ignore[no-untyped-def]
    """An independent count (one day at a time) for every counted deadline in the table, across a whole year."""
    rules = [r for r in ruleset if r.kind == "deadline" and r.unit in ("days", "weeks", "business_days")
             and r.anchor in ("event_date", "event_end_date")]
    assert rules
    day = date(2026, 11, 1)
    while day < date(2028, 3, 2):
        for rule in rules:
            want = day
            remaining = rule.offset * (7 if rule.unit == "weeks" else 1)
            step = -1 if rule.direction == "before" else 1
            while remaining:
                want += timedelta(days=step)
                if rule.unit != "business_days" or want.weekday() < 5:
                    remaining -= 1
            assert deadlines.due_date(rule, start=day, end=day) == want, (rule.id, day)
        day += timedelta(days=1)


@pytest.mark.parametrize("unit,offset", [("days", 60), ("weeks", 2), ("weeks", 6), ("months", 3), ("months", 1), ("business_days", 3)])
def test_earliest_event_date_meeting_a_deadline_is_the_first_that_does(unit: str, offset: int) -> None:
    rule = _rule(unit=unit, offset=offset)
    as_of = date(2026, 11, 1)
    while as_of < date(2028, 4, 1):
        earliest = deadlines.latest_start_meeting(rule, as_of)
        assert earliest is not None
        due = deadlines.due_date(rule, start=earliest)
        before = deadlines.due_date(rule, start=earliest - timedelta(days=1))
        assert due is not None and due >= as_of, (unit, offset, as_of, earliest)
        assert before is not None and before < as_of, (unit, offset, as_of, earliest)
        as_of += timedelta(days=1)


def test_no_earliest_date_for_deadlines_after_the_event_or_without_a_date() -> None:
    assert deadlines.latest_start_meeting(_rule(direction="after"), date(2026, 11, 15)) is None
    assert deadlines.latest_start_meeting(_rule(unit="academic_weeks"), date(2026, 11, 15)) is None
    assert deadlines.latest_start_meeting(_rule(anchor="initial_payment_due_date"), date(2026, 11, 15)) is None


def test_the_stricter_of_two_disagreeing_deadlines(ruleset) -> None:  # type: ignore[no-untyped-def]
    get = ruleset.get
    # Same anchor: more lead time before the event is stricter.
    assert deadlines.stricter_of(get("tes-decorations-terms"), get("tes-decorations-faq"), None, None) == "tes-decorations-terms"
    assert deadlines.stricter_of(get("tes-cancellation-large-terms"), get("tes-cancellation-large-faq"), None, None) == "tes-cancellation-large-faq"
    # With dates, the earlier date wins.
    assert deadlines.stricter_of(get("tes-decorations-terms"), get("tes-decorations-faq"), date(2027, 3, 1), date(2027, 3, 8)) == "tes-decorations-terms"
    # 9 academic weeks before the first payment is earlier than 8 weeks before the event or travel.
    assert deadlines.stricter_of(get("usg-deadline-travel"), get("usg-faq-deadline-new-vendors-travel"), None, None) == "usg-deadline-travel"
    assert deadlines.stricter_of(get("usg-deadline-travel"), get("usg-faq-professional-travel-eight-weeks"), None, None) == "usg-deadline-travel"
    # The same lead time from different anchors cannot be ordered without the payment date.
    assert deadlines.stricter_of(get("usg-deadline-vendor"), get("usg-page-deadline-event-date"), None, None) is None
    # After a notification: 48 hours is never longer than 2 business days; 2 business days is shorter than 3.
    assert deadlines.stricter_of(get("usg-incomplete-two-business-days"), get("usg-incomplete-48-hours"), None, None) == "usg-incomplete-48-hours"
    assert deadlines.stricter_of(get("usg-incomplete-two-business-days"), get("usg-faq-incomplete-three-business-days"), None, None) == "usg-incomplete-two-business-days"
    assert deadlines.stricter_of(get("usg-incomplete-48-hours"), get("usg-faq-incomplete-three-business-days"), None, None) == "usg-incomplete-48-hours"
