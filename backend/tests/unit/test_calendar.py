from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pytest

from app.rules import CalendarLoadError, load_calendar, load_rules
from tests.conftest import RULES_DIR


@pytest.fixture(scope="module")
def calendar():  # type: ignore[no-untyped-def]
    return load_calendar(RULES_DIR)


def test_calendar_is_confirmed_by_a_person_but_its_assumptions_are_not(calendar) -> None:  # type: ignore[no-untyped-def]
    assert calendar.verified == "read"  # confirmed by the user on 2026-11-14 (PLAN.md Phase 0)
    assert "Confirmed by a human" in (calendar.verification_note or "")
    assert calendar.business_days.verified == "unverified"
    assert calendar.academic_weeks.verified == "unverified"
    assert calendar.academic_weeks.definition is None


def test_calendar_rule_carries_the_same_verification(calendar) -> None:  # type: ignore[no-untyped-def]
    assert load_rules(RULES_DIR).get(calendar.id).verified == calendar.verified


def test_spring_2027_dates_from_the_registrar(calendar) -> None:  # type: ignore[no-untyped-def]
    spring = calendar.term("spring-2027")
    assert spring.classes_begin == date(2027, 1, 11)
    assert spring.classes_end == date(2027, 4, 30)
    assert (spring.study_days.start, spring.study_days.end) == (date(2027, 5, 1), date(2027, 5, 4))
    assert (spring.final_exams.start, spring.final_exams.end) == (date(2027, 5, 5), date(2027, 5, 12))
    assert [(b.start, b.end) for b in spring.breaks] == [(date(2027, 3, 14), date(2027, 3, 21))]
    assert {h.start for h in spring.holidays} == {date(2027, 1, 18), date(2027, 2, 15)}


def test_weekdays_match_the_source_labels(calendar) -> None:  # type: ignore[no-untyped-def]
    # The Registrar prints the weekday beside each date: "Classes Begin Mon January 11" and so on.
    spring = calendar.term("spring-2027")
    assert spring.classes_begin.strftime("%a") == "Mon"
    assert spring.classes_end.strftime("%a") == "Fri"
    assert spring.study_days.start.strftime("%a") == "Sat"
    assert spring.final_exams.start.strftime("%a") == "Wed"
    assert spring.final_exams.end.strftime("%a") == "Wed"
    fall = calendar.term("fall-2026")
    assert fall.classes_begin.strftime("%a") == "Mon"


def test_calendar_queries(calendar) -> None:  # type: ignore[no-untyped-def]
    assert calendar.is_break(date(2027, 3, 16))
    assert calendar.is_break(date(2026, 12, 25))  # winter recess
    assert not calendar.is_break(date(2027, 3, 22))
    assert calendar.is_university_holiday(date(2027, 1, 18))
    assert calendar.is_study_day_or_final_exam(date(2027, 5, 6))
    assert not calendar.is_study_day_or_final_exam(date(2027, 4, 30))
    assert calendar.term_for(date(2027, 2, 1)).id == "spring-2027"
    assert calendar.term_for(date(2026, 12, 25)) is None
    assert calendar.covers(date(2026, 12, 25))
    assert not calendar.covers(date(2028, 1, 1))


def _break(rules_copy: Path, change) -> None:  # type: ignore[no-untyped-def]
    path = rules_copy / "calendar.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    change(data)
    path.write_text(json.dumps(data), encoding="utf-8")


@pytest.mark.parametrize(
    ("change", "fragment"),
    [
        (lambda d: d["terms"][1].update(classes_end="2027-01-01"), "classes_end must be after classes_begin"),
        (lambda d: d["terms"][1]["breaks"][0].update(end="2027-03-01"), "end 2027-03-01 is before start"),
        (lambda d: d["terms"][1].update(source_text="Spring Semester 2027 begins whenever you like, honestly."), "not in the snapshot"),
        (lambda d: d["terms"].reverse(), "date order"),
        (lambda d: d.update(verified="read", verification_note=None) or d.pop("verification_note"), None),
        (lambda d: d["terms"][1]["holidays"].append({"name": "Made up", "start": "2027-08-01", "end": "2027-08-01"}), "outside the term"),
        (lambda d: d.pop("timezone"), "timezone"),
    ],
)
def test_malformed_calendar_is_rejected(rules_copy: Path, change, fragment) -> None:  # type: ignore[no-untyped-def]
    _break(rules_copy, change)
    if fragment is None:
        # Marking the calendar 'read' is allowed by the schema; validate_rules.py then reports that the
        # calendar rule and the file disagree (covered in test_scripts).
        load_calendar(rules_copy)
        return
    with pytest.raises(CalendarLoadError) as caught:
        load_calendar(rules_copy)
    assert fragment in str(caught.value)
