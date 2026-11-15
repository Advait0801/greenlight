"""Phase 0, iteration 2 (break): malformed academic calendars.

The calendar drives every "no USG funding during breaks, study days or finals" check, every
"no socials on study days or finals" check and every business-day count. A calendar whose
dates are impossible, overlap, or contradict the Registrar text it quotes must be refused with
a CalendarLoadError, never loaded.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from app.rules import CalendarLoadError, load_calendar


def _edit(rules_dir: Path, change: Callable[[dict[str, Any]], None]) -> None:
    path = rules_dir / "calendar.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    change(data)
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


def _spring(data: dict[str, Any]) -> dict[str, Any]:
    return next(term for term in data["terms"] if term["id"] == "spring-2027")


def _summer(data: dict[str, Any]) -> dict[str, Any]:
    return next(term for term in data["terms"] if term["id"] == "summer-2027")


def _refused(rules_dir: Path) -> list[str]:
    with pytest.raises(CalendarLoadError) as caught:
        load_calendar(rules_dir)
    return caught.value.problems


def _finals_during_classes(data: dict[str, Any]) -> None:
    spring = _spring(data)
    spring.pop("study_days")
    spring["final_exams"] = {"name": "Exams", "start": "2027-04-20", "end": "2027-05-12"}


@pytest.mark.parametrize(
    "change",
    [
        # Without study days nothing checks that exams come after classes end.
        _finals_during_classes,
        # A recess in the middle of spring classes marks class days as a break.
        lambda d: d["recesses"].append({"name": "Bogus Recess", "start": "2027-02-01", "end": "2027-02-28"}),
        # Winter recess starting during fall exams.
        lambda d: d["recesses"][0].update(start="2026-12-10"),
        # Commencement before the term even starts.
        lambda d: _spring(d).update(commencement={"name": "Commencement", "start": "2026-01-01", "end": "2026-01-02"}),
    ],
    ids=["finals-during-classes", "recess-inside-a-term", "recess-overlaps-exams", "commencement-outside-term"],
)
def test_overlapping_or_misplaced_periods_are_refused(rules_copy: Path, change: Callable[[dict[str, Any]], None]) -> None:
    _edit(rules_copy, change)
    _refused(rules_copy)


def test_date_given_as_a_number_is_refused(rules_copy: Path) -> None:
    """A Unix timestamp for classes_begin is currently converted to a date without complaint."""
    _edit(rules_copy, lambda d: _spring(d).update(classes_begin=1799625600))
    _refused(rules_copy)


@pytest.mark.parametrize(
    "change",
    [
        # The quoted text says "Spring Recess Sun-Sun March 14-21".
        lambda d: _spring(d)["breaks"][0].update(start="2027-03-21", end="2027-03-28"),
        # The quoted text says "Classes End Fri April 30".
        lambda d: _spring(d).update(classes_end="2027-04-23"),
        # The quoted text lists "Martin Luther King Jr. Day Holiday Mon January 18".
        lambda d: _spring(d)["holidays"].pop(0),
        # Spring quoting the summer paragraph: still "in the snapshot", but not this term's text.
        lambda d: _spring(d).update(source_text=_summer(d)["source_text"]),
    ],
    ids=["spring-recess-shifted", "classes-end-moved", "holiday-dropped", "wrong-term-quoted"],
)
def test_dates_that_contradict_the_quoted_registrar_text_are_refused(
    rules_copy: Path, change: Callable[[dict[str, Any]], None]
) -> None:
    """The loader checks that each term's source_text is in the snapshot, but not that the dates
    encoded beside it are the dates that text states. Shifting spring recess by a week loads, and
    an event on March 16, 2027 (inside the real recess) would no longer be flagged."""
    _edit(rules_copy, change)
    _refused(rules_copy)


def test_calendar_effective_date_must_be_the_source_version_date(rules_copy: Path) -> None:
    """Rules must carry the manifest's version_date as effective_date; the calendar is not checked."""
    _edit(rules_copy, lambda d: d.update(effective_date="2019-01-01"))
    _refused(rules_copy)


def test_calendar_that_is_not_utf8_is_a_load_error_not_a_crash(rules_copy: Path) -> None:
    """Currently raises UnicodeDecodeError, which neither the app nor validate_rules.py catches."""
    (rules_copy / "calendar.json").write_bytes(b"\xff\xfe\x00 not a calendar")
    _refused(rules_copy)
