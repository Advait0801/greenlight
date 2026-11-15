"""Greenlight's copy of USG's Funding Application Deadlines table, looked up by event date.

The table is keyed by event week and gives a 6-week and a 9-week application deadline (always a Wednesday). The
copy in rules/sources/ was transcribed by hand and nobody has confirmed it against the sheet, so rule
usg-academic-week-definition (unverified) says no deadline may be given as certain from it. Callers show what it
says only as "USG's table, as transcribed (unconfirmed)", yellow, next to the date that is certain.

Pure Python, no AI. Nothing here computes a deadline: it only reads rows.
"""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass
from datetime import date, timedelta
from functools import lru_cache
from pathlib import Path
from typing import Literal

from app.rules import RuleSet

DEFINITION_RULE = "usg-academic-week-definition"
HEADER_END = "==== END OF SNAPSHOT HEADER ===="
Column = Literal["6_week", "9_week"]
COLUMNS: tuple[Column, ...] = ("6_week", "9_week")


@dataclass(frozen=True)
class TableRow:
    start: date
    end: date
    deadline_6_week: date | None
    deadline_9_week: date | None
    # "N/A" in the sheet (the first weeks of fall): no deadline can be met, so no funding those weeks.
    not_applicable: bool


@dataclass(frozen=True)
class TableLookup:
    """What the table says for one event date and column.

    status: "date"         the table gives `deadline`
            "no_deadline"  the row is blank (breaks, study days, finals): USG funds nothing that week
            "not_applicable" the row says N/A (the first weeks of fall)
            "not_in_table" no row covers the date (for example May 2027 onward)
    """

    status: Literal["date", "no_deadline", "not_applicable", "not_in_table"]
    deadline: date | None
    row: TableRow | None
    to_confirm: bool


class DeadlineTableError(ValueError):
    pass


def _parse_day(value: str) -> date | None:
    value = value.strip()
    if not value or value.upper() == "N/A":
        return None
    return date.fromisoformat(value)


@lru_cache(maxsize=4)
def _rows(path: str, mtime_ns: int) -> tuple[TableRow, ...]:
    text = Path(path).read_text(encoding="utf-8")
    if HEADER_END in text:
        text = text.split(HEADER_END, 1)[1]
    lines = [line for line in text.splitlines() if line.strip() and not line.lstrip().startswith("#")]
    reader = csv.DictReader(io.StringIO("\n".join(lines)))
    rows: list[TableRow] = []
    for record in reader:
        try:
            start = date.fromisoformat(record["event_week_start"].strip())
            end = date.fromisoformat(record["event_week_end"].strip())
            six, nine = record["deadline_6_week"], record["deadline_9_week"]
            rows.append(TableRow(start=start, end=end, deadline_6_week=_parse_day(six), deadline_9_week=_parse_day(nine),
                                 not_applicable=six.strip().upper() == "N/A" or nine.strip().upper() == "N/A"))
        except (KeyError, AttributeError, ValueError) as exc:
            raise DeadlineTableError(f"unreadable row in the USG deadline table copy: {record}") from exc
    rows.sort(key=lambda row: row.start)
    for earlier, later in zip(rows, rows[1:], strict=False):
        if later.start <= earlier.end:
            raise DeadlineTableError(f"rows starting {earlier.start} and {later.start} overlap")
    return tuple(rows)


def table_rows(ruleset: RuleSet, sources_dir: Path) -> tuple[TableRow, ...]:
    rule = ruleset.get(DEFINITION_RULE)
    name = rule.params.get("deadline_table_snapshot")
    if not isinstance(name, str) or "/" in name or "\\" in name:
        raise DeadlineTableError(f"{DEFINITION_RULE} names no deadline table snapshot")
    path = sources_dir / name
    return _rows(str(path), path.stat().st_mtime_ns)


def _rows_to_confirm(ruleset: RuleSet) -> set[date]:
    raw = ruleset.get(DEFINITION_RULE).params.get("rows_to_confirm", [])
    return {date.fromisoformat(value) for value in raw if isinstance(value, str)}


def lookup(ruleset: RuleSet, sources_dir: Path, day: date, column: Column) -> TableLookup:
    """The row for `day`: the row whose dates contain it, or for a Saturday or Sunday the row of the Monday before it
    (rule usg-academic-week-definition, params.date_to_row)."""
    rows = table_rows(ruleset, sources_dir)
    monday = day - timedelta(days=day.weekday())
    found = next((row for row in rows if row.start <= day <= row.end), None)
    if found is None and day.weekday() >= 5:
        found = next((row for row in rows if row.start <= monday <= row.end), None)
    if found is None:
        return TableLookup(status="not_in_table", deadline=None, row=None, to_confirm=False)
    to_confirm = found.start in _rows_to_confirm(ruleset)
    if found.not_applicable:
        return TableLookup(status="not_applicable", deadline=None, row=found, to_confirm=to_confirm)
    deadline = found.deadline_6_week if column == "6_week" else found.deadline_9_week
    if deadline is None:
        return TableLookup(status="no_deadline", deadline=None, row=found, to_confirm=to_confirm)
    return TableLookup(status="date", deadline=deadline, row=found, to_confirm=to_confirm)
