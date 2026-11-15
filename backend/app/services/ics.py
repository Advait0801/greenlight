"""An iCalendar (.ics, RFC 5545) file of an event packet's dated items, for any calendar app.

Every date comes from the packet (the deadline calculator). Items are all-day events. Text is escaped and
lines are folded at 75 octets as the standard requires.
"""

from __future__ import annotations

import hashlib
from datetime import UTC, date, datetime, timedelta

from app.schemas.events import EventPacket

PRODID = "-//Greenlight//Event packet//EN"


def _escape(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    # Control characters other than the newline are not allowed in iCalendar text.
    text = "".join(ch for ch in text if ch == "\n" or (ord(ch) >= 32 and ord(ch) != 127))
    return text.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")


def _fold(line: str) -> list[str]:
    data = line.encode("utf-8")
    if len(data) <= 75:
        return [line]
    out: list[str] = []
    current = b""
    limit = 75
    for char in line:
        encoded = char.encode("utf-8")
        if len(current) + len(encoded) > limit:
            out.append(current.decode("utf-8"))
            current = b""
            limit = 74  # continuation lines start with a space
        current += encoded
    out.append(current.decode("utf-8"))
    return [out[0], *(" " + part for part in out[1:])]


def _day(value: date) -> str:
    return value.strftime("%Y%m%d")


def _vevent(uid: str, start: date, end: date, summary: str, description: str, url: str | None, stamp: str) -> list[str]:
    lines = [
        "BEGIN:VEVENT",
        f"UID:{uid}",
        f"DTSTAMP:{stamp}",
        f"DTSTART;VALUE=DATE:{_day(start)}",
        f"DTEND;VALUE=DATE:{_day(end)}",
        f"SUMMARY:{_escape(summary)}",
        f"DESCRIPTION:{_escape(description)}",
        "TRANSP:TRANSPARENT",
    ]
    if url:
        lines.append(f"URL:{url}")
    lines.append("END:VEVENT")
    return lines


def packet_to_ics(packet: EventPacket, *, now: datetime | None = None) -> str:
    stamp = (now or datetime.now(UTC)).astimezone(UTC).strftime("%Y%m%dT%H%M%SZ")
    name = packet.event.name or "Club event"
    seed = f"{name}|{packet.event.event_date}|{packet.event.end_date}"
    key = hashlib.sha256(seed.encode("utf-8")).hexdigest()[:16]
    lines = ["BEGIN:VCALENDAR", "VERSION:2.0", f"PRODID:{PRODID}", "CALSCALE:GREGORIAN", "METHOD:PUBLISH",
             f"X-WR-CALNAME:{_escape('Greenlight: ' + name)}"]
    if packet.event.event_date is not None:
        last = packet.event.end_date or packet.event.event_date
        lines += _vevent(f"{key}-event@greenlight", packet.event.event_date, last + timedelta(days=1), name,
                         "The event. " + packet.notice, None, stamp)
    for o in packet.obligations:
        if o.due is None or o.superseded_by is not None:
            continue
        summary = f"{o.status_label}: {o.title}"
        if o.past_due:
            summary = f"Passed: {o.title}"
        description = (f"{o.message}\n\nOwner: {o.owner_office}\nWhy this date: {o.due_note or ''}\n"
                       f"Source: {o.citation.source}\n{o.link}\n\n{packet.notice}")
        lines += _vevent(f"{key}-{o.rule_id}@greenlight", o.due, o.due + timedelta(days=1), summary, description, o.link, stamp)
    for o in packet.obligations:
        if o.due is not None or o.contact_by is None or o.superseded_by is not None:
            continue
        description = (f"{o.message}\n\n{o.note or ''}\nOwner: {o.owner_office}\nSource: {o.citation.source}\n{o.link}\n\n{packet.notice}")
        lines += _vevent(f"{key}-{o.rule_id}-contact@greenlight", o.contact_by, o.contact_by + timedelta(days=1),
                         f"Contact by: {o.title}", description, o.link, stamp)
    lines.append("END:VCALENDAR")
    folded = [part for line in lines for part in _fold(line)]
    return "\r\n".join(folded) + "\r\n"
