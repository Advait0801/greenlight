"""Evaluator for the event sentence test set (Phase 2).

Two runs over the 30 cases:
  engine      the rule engine and deadline calculator on the test set's own attributes and dates, so a
              wrong rule or date shows up without any AI involved;
  end_to_end  the sentence read by the reading step (AI_MODE=recorded replays saved answers), then the
              same engine. This is the run the exit criterion is about.

An obligation list matches when it holds exactly the expected rules. "caught" counts expected obligations
found, "missed" expected obligations absent with no yellow 'check with the office' note standing in for them,
"wrongly_flagged" obligations listed that the test set does not expect.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from app.rules import RuleSet, get_calendar
from app.schemas.events import EventFacts, EventPacket
from app.services.rule_engine import build_packet

FIELDS = ("status", "due", "violated", "past_due")


def _facts_from_expected(expected: dict[str, Any]) -> EventFacts:
    return EventFacts(
        event_date=expected["event_date"],
        end_date=expected["end_date"],
        venue=expected["venue"],
        headcount=expected["headcount"],
        attributes=expected["attributes"],
    )


def compare(packet: EventPacket, expected: dict[str, Any]) -> dict[str, Any]:
    got = {o.rule_id: o for o in packet.obligations}
    want = {o["rule_id"]: o for o in expected["obligations"]}
    missing = sorted(set(want) - set(got))
    extra = sorted(set(got) - set(want))
    field_diffs = []
    for rule_id, entry in want.items():
        o = got.get(rule_id)
        if o is None:
            continue
        actual = {"status": o.status, "due": o.due.isoformat() if o.due else None, "violated": o.violated, "past_due": o.past_due}
        for key in FIELDS:
            if actual[key] != entry[key]:
                field_diffs.append({"rule_id": rule_id, "field": key, "got": actual[key], "want": entry[key]})
    got_conflicts = {frozenset(c.rules): c.applied for c in packet.source_conflicts}
    want_conflicts = {frozenset(c["rules"]): c["applied"] for c in expected["source_conflicts"]}
    # A missing expected obligation is 'silent' unless the packet says, in yellow, to check with the office.
    yellow_cover = any(o.status == "check_with_office" for o in packet.obligations) or bool(packet.questions)
    return {
        "match": not missing and not extra,
        "missing": missing,
        "silently_missing": missing if not yellow_cover else [],
        "extra": extra,
        "field_diffs": field_diffs,
        "conflicts_match": got_conflicts == want_conflicts,
        "found": len(set(want) & set(got)),
    }


def _run(data: dict[str, Any], ruleset: RuleSet, facts_for: Any) -> dict[str, Any]:
    calendar = get_calendar()
    rows = []
    for case in data["cases"]:
        facts, error = facts_for(case)
        if facts is None:
            rows.append({"id": case["id"], "match": False, "error": error, "missing": [o["rule_id"] for o in case["expected"]["obligations"]],
                         "silently_missing": [], "extra": [], "field_diffs": [], "conflicts_match": False, "found": 0})
            continue
        packet = build_packet(facts, ruleset, calendar, date.fromisoformat(case["as_of"]))
        rows.append({"id": case["id"], **compare(packet, case["expected"])})
    return {
        "matched": sum(1 for row in rows if row["match"]),
        "cases": len(rows),
        "caught": sum(row["found"] for row in rows),
        "missed": sum(len(row["missing"]) for row in rows),
        "silently_missing": sum(len(row["silently_missing"]) for row in rows),
        "wrongly_flagged": sum(len(row["extra"]) for row in rows),
        "field_diffs": sum(len(row["field_diffs"]) for row in rows),
        "conflicts_matched": sum(1 for row in rows if row["conflicts_match"]),
        "details": [row for row in rows if not row["match"] or row["field_diffs"] or not row["conflicts_match"]],
    }


def _parsed_facts(case: dict[str, Any]) -> tuple[EventFacts | None, str | None]:
    from app.services.event_intake import IntakeError, parse_sentence

    try:
        parsed = parse_sentence(case["sentence"], as_of=date.fromisoformat(case["as_of"]))
    except IntakeError as exc:
        return None, str(exc)
    return parsed.facts, None


def evaluate(data: dict[str, Any], ruleset: RuleSet) -> dict[str, Any]:
    engine = _run(data, ruleset, lambda case: (_facts_from_expected(case["expected"]), None))
    end_to_end = _run(data, ruleset, _parsed_facts)
    notes = (
        f"end to end (recorded reading step): {end_to_end['matched']}/{end_to_end['cases']} obligation lists match, "
        f"{end_to_end['silently_missing']} silently missing; engine on the test set's attributes: "
        f"{engine['matched']}/{engine['cases']} match, {engine['field_diffs']} status/date differences, "
        f"{engine['conflicts_matched']}/{engine['cases']} conflict lists match"
    )
    return {
        "caught": end_to_end["caught"],
        "missed": end_to_end["missed"],
        "wrongly_flagged": end_to_end["wrongly_flagged"],
        "details": {"end_to_end": end_to_end, "engine": engine},
        "notes": notes,
    }
