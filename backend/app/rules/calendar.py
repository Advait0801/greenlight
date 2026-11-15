"""The academic calendar (rules/calendar.json), used by the deadline calculator.

The calendar is marked unverified until a human confirms it (PLAN.md Phase 0). Anything
computed from it must therefore be shown with that caveat.
"""

from __future__ import annotations

import json
import re
from datetime import date, timedelta
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from app.jsonutil import StrictJSONError, loads_strict
from app.rules.schema import IsoDate, Verified
from app.rules.snapshots import ManifestError, canonical_url, load_manifest, snapshot_text, text_in_snapshot


class DateRange(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str = Field(min_length=2)
    start: IsoDate
    end: IsoDate

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
    classes_begin: IsoDate
    classes_end: IsoDate
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
        if self.final_exams and self.final_exams.start <= self.classes_end:
            raise ValueError(f"{self.id}: final exams must start after classes end")
        if self.commencement and (
            self.commencement.start < self.classes_end or self.commencement.end > self.last_day + timedelta(days=7)
        ):
            raise ValueError(f"{self.id}: commencement must fall at the end of the term")
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
    effective_date: IsoDate
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
        for recess in self.recesses:
            for term in self.terms:
                if recess.start <= term.last_day and recess.end >= term.classes_begin:
                    raise ValueError(f"recess '{recess.name}' overlaps term {term.id}")
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


_MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
           "November", "December"]
_DOW = "Mon|Tue|Wed|Thu|Fri|Sat|Sun"
_ENTRY = re.compile(
    rf"(?P<dow>(?:{_DOW})(?:-(?:{_DOW}))?) (?P<m1>{'|'.join(_MONTHS)}) (?P<d1>\d{{1,2}})"
    rf"(?:-(?:(?P<m2>{'|'.join(_MONTHS)}) )?(?P<d2>\d{{1,2}}))?"
)
_HEADING = re.compile(r"^(?P<season>Fall|Spring|Summer) (?:Semester|Session) (?P<year>\d{4})\b")
_IGNORED = {"Open Registration", "Registration", "Move-In"}


def _parse_term_text(text: str) -> tuple[str, int, list[tuple[str, date, date, str]]]:
    """Read the Registrar's lines out of a term's quoted text: (season, year, [(name, start, end, weekdays)])."""
    heading = _HEADING.match(text)
    if heading is None:
        raise ValueError("source_text does not start with a term heading such as 'Spring Semester 2027'")
    year = int(heading["year"])
    body = text[heading.end():]
    entries = []
    previous_end, previous_month = 0, None
    for match in _ENTRY.finditer(body):
        name = re.sub(r"^\d+ instructional days ", "", body[previous_end:match.start()].strip())
        previous_end = match.end()
        m1 = _MONTHS.index(match["m1"]) + 1
        if previous_month is not None and m1 < previous_month:
            year += 1
        previous_month = m1
        start = date(year, m1, int(match["d1"]))
        end = start
        if match["d2"]:
            m2 = _MONTHS.index(match["m2"]) + 1 if match["m2"] else m1
            end = date(year + (1 if m2 < m1 else 0), m2, int(match["d2"]))
        entries.append((name, start, end, match["dow"]))
    return heading["season"], int(heading["year"]), entries


def _weekday(day: date) -> str:
    return day.strftime("%a")


def check_against_text(calendar: AcademicCalendar) -> list[str]:
    """Every date in the calendar must be the date its quoted Registrar text states, and every line
    of that text must be in the calendar. A shifted, added or dropped date is a problem."""
    problems: list[str] = []
    recesses_in_text: set[tuple[str, date, date]] = set()
    for term in calendar.terms:
        try:
            season, year, entries = _parse_term_text(term.source_text)
        except ValueError as exc:
            problems.append(f"term {term.id}: {exc}")
            continue
        if not (term.name.startswith(season) and str(year) in term.name):
            problems.append(f"term {term.id}: its source_text is the {season} {year} text, not {term.name}'s")
            continue
        holidays, breaks = set(), set()
        singles: dict[str, tuple[date, date]] = {}
        for name, start, end, dow in entries:
            days = dow.split("-")
            if len(days) == 2 and (days[0] != _weekday(start) or days[1] != _weekday(end)):
                problems.append(f"term {term.id}: '{name}' weekdays {dow} do not match {start} to {end}")
            if len(days) == 1 and start == end and days[0] != _weekday(start):
                problems.append(f"term {term.id}: '{name}' is a {dow} in the text but {start} is a {_weekday(start)}")
            if name in _IGNORED:
                continue
            if name in ("Classes Begin", "Classes End", "Study Days", "Exams", "Commencement"):
                singles[name] = (start, end)
            elif name.endswith("Recess") and name.startswith("Winter"):
                recesses_in_text.add((name, start, end))
            elif name.endswith("Recess"):
                breaks.add((name, start, end))
            elif "Holiday" in name or name == "Juneteenth":
                holidays.add((name, start, end))
            else:
                problems.append(f"term {term.id}: the quoted text has a line '{name}' the calendar does not recognise")

        def compare(label: str, encoded: object, stated: object) -> None:
            if encoded != stated:
                problems.append(f"term {term.id}: {label} is {encoded} in the calendar but {stated} in its quoted text")

        compare("classes_begin", term.classes_begin, singles.get("Classes Begin", (None,))[0])
        compare("classes_end", term.classes_end, singles.get("Classes End", (None,))[0])
        for label, field, key in (("study_days", term.study_days, "Study Days"), ("final_exams", term.final_exams, "Exams"),
                                  ("commencement", term.commencement, "Commencement")):
            compare(label, (field.start, field.end) if field else None, singles.get(key))
        compare("holidays", {(h.name, h.start, h.end) for h in term.holidays}, holidays)
        compare("breaks", {(b.name, b.start, b.end) for b in term.breaks}, breaks)
    encoded_recesses = {(r.name, r.start, r.end) for r in calendar.recesses}
    if encoded_recesses != recesses_in_text:
        problems.append(f"recesses are {encoded_recesses} in the calendar but {recesses_in_text} in the quoted texts")
    return problems


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
    except UnicodeDecodeError as exc:
        raise CalendarLoadError([f"{path.name}: not UTF-8 text ({exc.reason})"]) from exc
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
            if source.version_date != calendar.effective_date.isoformat():
                problems.append(
                    f"effective_date {calendar.effective_date} differs from the source's version date {source.version_date}"
                )
            snapshot = snapshot_text(sources_dir, source)
            for term in calendar.terms:
                if not text_in_snapshot(term.source_text, snapshot):
                    problems.append(f"term {term.id}: source_text is not in the snapshot {source.snapshot}")
    except ManifestError as exc:
        problems.append(str(exc))
    problems.extend(check_against_text(calendar))
    if problems:
        raise CalendarLoadError(problems)
    return calendar
