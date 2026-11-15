"""The readiness tracker: counts and dates from the rule table, never a green on an unconfirmed rule."""

from __future__ import annotations

from datetime import date
from typing import Any

import pytest

from app.rules import get_ruleset
from app.schemas.common import Verdict
from app.services.recognition_readiness import OfficerStatus, ReadinessInput, readiness

POSITIONS = ["president", "vice president", "secretary", "treasurer", "programming chair"]


@pytest.fixture(scope="module")
def ruleset() -> Any:
    return get_ruleset()


def _everything(**overrides: Any) -> ReadinessInput:
    data: dict[str, Any] = dict(
        officers=[OfficerStatus(position=p, named=True, hazing_prevention=True, officer_learning_path=True,
                                commitment_to_community=True) for p in POSITIONS],
        additional_members=5, advisor_named=True, advisor_accepted=True, advisor_training=True, advisor_commitment=True,
        constitution_ready=True, accountability_document=True, positions_accepted=True,
    )
    data.update(overrides)
    return ReadinessInput(**data)


def _items(report: Any) -> dict[str, Any]:
    return {item.id: item for group in report.groups for item in group.items}


def test_five_officers_times_three_items(ruleset: Any) -> None:
    report = readiness(ruleset, ReadinessInput(), date(2026, 11, 15))
    officer_items = [i for g in report.groups if g.title.lower() in POSITIONS for i in g.items]
    assert len(officer_items) == 5 * 4  # named + three documents each
    assert report.overall is Verdict.RED


def test_key_dates_come_from_the_rules(ruleset: Any) -> None:
    report = readiness(ruleset, ReadinessInput(), date(2026, 11, 15))
    days = {k.day: k.days_left for k in report.key_dates}
    assert days == {date(2026, 10, 27): -19, date(2026, 11, 22): 7, date(2026, 12, 1): 16}
    for key in report.key_dates:
        assert key.citation.source_url.startswith("https://")


def test_member_shortfall_counts_officers(ruleset: Any) -> None:
    report = readiness(ruleset, _everything(additional_members=3), date(2026, 11, 15))
    members = _items(report)["members"]
    assert members.state == "to_do" and members.fix == "Add 2 more student members."
    exact = readiness(ruleset, _everything(additional_members=5), date(2026, 11, 15))
    assert _items(exact)["members"].state == "done"


def test_fewer_officers_raise_the_member_shortfall(ruleset: Any) -> None:
    given = _everything()
    given.officers[4].named = False
    members = _items(readiness(ruleset, given, date(2026, 11, 15)))["members"]
    assert members.state == "to_do" and "1 more" in (members.fix or "")


def test_all_ticked_is_never_fully_green(ruleset: Any) -> None:
    """The Clery course, accessibility module and EngageSC acceptance rest on unconfirmed or hedged rules."""
    report = readiness(ruleset, _everything(), date(2026, 11, 15))
    items = _items(report)
    assert report.overall is Verdict.YELLOW
    for key in ("advisor:clery", "accessibility", "accepted"):
        assert items[key].verdict is Verdict.YELLOW
    assert all(i.verdict is not Verdict.GREEN for i in items.values() if i.citation.display_severity != "red")


def test_after_the_window_closes_it_says_so(ruleset: Any) -> None:
    report = readiness(ruleset, ReadinessInput(), date(2026, 11, 23))
    assert "closed" in report.message and "not accepted" in report.message
    close = next(k for k in report.key_dates if k.day == date(2026, 11, 22))
    assert close.passed


def test_last_day_says_today(ruleset: Any) -> None:
    report = readiness(ruleset, ReadinessInput(), date(2026, 11, 22))
    assert report.message.endswith("today.")


def test_position_names_are_matched_loosely(ruleset: Any) -> None:
    given = ReadinessInput(officers=[OfficerStatus(position="  Vice   President ", named=True)])
    assert _items(readiness(ruleset, given, date(2026, 11, 15)))["vice president:named"].state == "done"


def test_negative_member_count_is_refused() -> None:
    with pytest.raises(ValueError):
        ReadinessInput(additional_members=-1)
