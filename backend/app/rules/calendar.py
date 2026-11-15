"""The academic calendar (rules/calendar.json), used by the deadline calculator.

The calendar is marked unverified until a human confirms it (PLAN.md Phase 0). Anything
computed from it must therefore be shown with that caveat.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from app.jsonutil import StrictJSONError, loads_strict
from app.rules.schema import Verified
from app.rules.snapshots import ManifestError, canonical_url, load_manifest, snapshot_text, text_in_snapshot


class DateRange(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str = Field(min_length=2)
    start: date
    end: date

    @model_validator(mode="after")
    def _ordered(self) -> DateRange:
        if self.end < self.start:
            raise ValueError(f"'{self.name}': end {self.end} is before start {self.start}")
        return self

    def __contains__(self, day: object) -> bool:
        return isinstance(day, date) and self.start <= day <= self.end


class Term(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str
    name: str
    source_text: str = Field(min_length=20)
    classes_begin: date
    classes_end: date
    study_days: DateRange | None = None
    final_exams: DateRange | None = None
    commencement: DateRange | None = None
    holidays: list[DateRange] = Field(default_factory=list)
    breaks: list[DateRange] = Field(default_factory=list)

    @model_validator(mode="after")
    def _consistent(self) -> Term:
        if self.classes_end <= self.classes_begin:
            raise ValueError(f"{self.id}: classes_end must be after classes_begin")
        last_day = self.final_exams.end if self.final_exams else self.classes_end
        for item in [*self.holidays, *self.breaks]:
            if item.start < self.classes_begin or item.end > last_day:
                raise ValueError(f"{self.id}: '{item.name}' falls outside the term")
        if self.study_days and self.study_days.start <= self.classes_end:
            raise ValueError(f"{self.id}: study days must start after classes end")
        if self.study_days and self.final_exams and self.final_exams.start <= self.study_days.end:
            raise ValueError(f"{self.id}: final exams must start after study days")
        return self

    @property
    def last_day(self) -> date:
        return self.final_exams.end if self.final_exams else self.classes_end


class Definition(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    definition: str | None
    verified: Verified
    note: str


class AcademicCalendar(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str
    title: str
    source: str
    source_url: str
    effective_date: date
    verified: Verified
    verification_note: str | None = None
    timezone: Literal["America/Los_Angeles"]
    terms: list[Term] = Field(min_length=1)
    recesses: list[DateRange] = Field(default_factory=list)
    business_days: Definition
    academic_weeks: Definition

    @model_validator(mode="after")
    def _consistent(self) -> AcademicCalendar:
        if self.verified != "read" and not self.verification_note:
            raise ValueError(f"a calendar marked '{self.verified}' needs a verification_note")
        ordered = sorted(self.terms, key=lambda term: term.classes_begin)
        if [term.id for term in ordered] != [term.id for term in self.terms]:
            raise ValueError("terms must be listed in date order")
        for earlier, later in zip(ordered, ordered[1:], strict=False):
            if later.classes_begin <= earlier.last_day:
                raise ValueError(f"terms {earlier.id} and {later.id} overlap")
        if len({term.id for term in self.terms}) != len(self.terms):
            raise ValueError("term ids must be unique")
        return self

    def term(self, term_id: str) -> Term:
        for term in self.terms:
            if term.id == term_id:
                return term
        raise KeyError(f"no term '{term_id}' in the calendar")

    def term_for(self, day: date) -> Term | None:
        """The term whose first class day to last exam day contains `day`."""
        for term in self.terms:
            if term.classes_begin <= day <= term.last_day:
                return term
        return None

    def is_university_holiday(self, day: date) -> bool:
        return any(day in holiday for term in self.terms for holiday in term.holidays)

    def is_break(self, day: date) -> bool:
        """A recess inside a term (e.g. spring recess) or between terms (e.g. winter recess)."""
        return any(day in item for term in self.terms for item in term.breaks) or any(
            day in recess for recess in self.recesses
        )

    def is_study_day_or_final_exam(self, day: date) -> bool:
        return any(
            (term.study_days is not None and day in term.study_days)
            or (term.final_exams is not None and day in term.final_exams)
            for term in self.terms
        )

    def covers(self, day: date) -> bool:
        """True if the calendar has data for this date (inside a term or a listed recess)."""
        return self.term_for(day) is not None or any(day in recess for recess in self.recesses)


class CalendarLoadError(Exception):
    def __init__(self, problems: list[str]) -> None:
        self.problems = problems
        lines = "\n".join(f"  - {problem}" for problem in problems)
        super().__init__(f"{len(problems)} problem(s) in rules/calendar.json:\n{lines}")


def load_calendar(rules_dir: Path) -> AcademicCalendar:
    path = rules_dir / "calendar.json"
    try:
        raw = loads_strict(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise CalendarLoadError([f"{path} not found"]) from exc
    except json.JSONDecodeError as exc:
        raise CalendarLoadError([f"not valid JSON (line {exc.lineno}, column {exc.colno}: {exc.msg})"]) from exc
    except StrictJSONError as exc:
        raise CalendarLoadError([str(exc)]) from exc
    try:
        calendar = AcademicCalendar.model_validate(raw)
    except ValidationError as exc:
        raise CalendarLoadError(
            [f"{'.'.join(str(p) for p in err['loc']) or 'calendar'}: {err['msg']}" for err in exc.errors()]
        ) from exc

    # Even while unverified, every term's quoted text must be in the snapshot it came from.
    problems: list[str] = []
    sources_dir = rules_dir / "sources"
    try:
        source = load_manifest(sources_dir).get(canonical_url(calendar.source_url))
        if source is None:
            problems.append(f"source_url {calendar.source_url} is not in rules/sources/manifest.json")
        else:
            snapshot = snapshot_text(sources_dir, source)
            for term in calendar.terms:
                if not text_in_snapshot(term.source_text, snapshot):
                    problems.append(f"term {term.id}: source_text is not in the snapshot {source.snapshot}")
    except ManifestError as exc:
        problems.append(str(exc))
    if problems:
        raise CalendarLoadError(problems)
    return calendar
