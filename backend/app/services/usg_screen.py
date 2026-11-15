"""USG screen (PROJECT_CONTEXT 4I): code only. Turns the applications clubs chose to send into the reviewer's queue, the
list of reasons a reviewer may cite, and the counts behind the "why applications fail" chart.

Every reason comes from the money check's own findings (the rule engine), with the rule text and source. The model
never picks a reason; it only words the opening paragraph of a denial draft (app/services/denial_draft.py).
"""

from __future__ import annotations

from collections import Counter
from datetime import date, datetime
from typing import Any

from pydantic import BaseModel

from app.models import SentApplication
from app.rules import RuleSet
from app.schemas.common import PRECHECK_NOTICE, VERDICT_LABELS, Citation, Verdict

# Findings a reviewer may cite in a denial reason. Green findings are never a reason.
CITABLE = (Verdict.RED, Verdict.YELLOW, Verdict.OFFICE_DECIDES)


class Reason(BaseModel):
    rule_id: str
    verdict: Verdict
    verdict_label: str
    where: str
    message: str
    fix: str | None
    citation: Citation


class QueueItem(BaseModel):
    id: int
    reference: str
    club_name: str
    event_name: str
    event_date: date | None
    sent_at: datetime
    verdict: Verdict
    verdict_label: str
    total_text: str
    counts: dict[str, int]
    denial_status: str


class ApplicationDetail(QueueItem):
    fund_name: str | None
    lines: list[dict[str, Any]]
    reasons: list[Reason]
    denial_rule_ids: list[str]
    denial_draft: str | None
    denial_approved_text: str | None
    denial_approved_by: str | None
    notice: str


class FailureRow(BaseModel):
    rule_id: str
    title: str
    applications: int
    citation: Citation | None


class FailureStats(BaseModel):
    applications: int
    rows: list[FailureRow]
    approved_denials: int
    note: str


def _money(cents: int) -> str:
    whole, part = divmod(abs(cents), 100)
    return f"{'-' if cents < 0 else ''}${whole:,}.{part:02d}"


def reasons(report: dict[str, Any]) -> list[Reason]:
    """Every red, yellow or office-decides finding in a stored money check report, one per rule and place."""
    out: list[Reason] = []
    seen: set[tuple[str, str]] = set()

    def add(raw: dict[str, Any] | None, where: str) -> None:
        if not raw:
            return
        verdict = Verdict(raw["verdict"])
        key = (raw["rule_id"], where)
        if verdict not in CITABLE or key in seen:
            return
        seen.add(key)
        out.append(Reason(rule_id=raw["rule_id"], verdict=verdict, verdict_label=VERDICT_LABELS[verdict], where=where,
                          message=raw["message"], fix=raw.get("fix"), citation=Citation.model_validate(raw["citation"])))

    for line in report.get("lines", []):
        where = f"Line {line['line']}: {line.get('item') or 'item'}"
        for entry in line.get("findings", []):
            add(entry.get("finding"), where)
        add((line.get("vendor_check") or {}).get("finding"), where)
    for entry in report.get("application", []):
        add(entry.get("finding"), "Whole application")
    from app.rules import get_ruleset

    ruleset = get_ruleset()
    for obligation in report.get("dates", []):
        rule_id = obligation.get("rule_id", "")
        # A duty due after the event (evaluation, final invoices, fixing a returned application) is not something the
        # application breaks, so it is never a reason to deny it (phase 5 iteration 2).
        if rule_id in ruleset and ruleset.get(rule_id).direction == "after":
            continue
        add(obligation.get("finding"), "Dates")
    order = {Verdict.RED: 0, Verdict.OFFICE_DECIDES: 1, Verdict.YELLOW: 2}
    out.sort(key=lambda r: (order.get(r.verdict, 3), r.where, r.rule_id))
    return out


def queue_item(row: SentApplication) -> QueueItem:
    report = row.report
    verdict = Verdict(report["verdict"])
    return QueueItem(id=row.id, reference=row.reference, club_name=row.club_name, event_name=row.event_name,
                     event_date=row.event_date, sent_at=row.sent_at, verdict=verdict, verdict_label=VERDICT_LABELS[verdict],
                     total_text=_money(int(report.get("totals", {}).get("total_cents", 0))),
                     counts={k: int(v) for k, v in report.get("counts", {}).items()}, denial_status=row.denial_status)


def _line_verdict(line: dict[str, Any]) -> str:
    """The screen has no vendor panel, so a green line from a vendor not shown on USG's list needs a look (final review F3)."""
    if line["verdict"] == Verdict.GREEN.value and (line.get("vendor_check") or {}).get("status") != "on_list":
        return Verdict.YELLOW.value
    return str(line["verdict"])


def detail(row: SentApplication) -> ApplicationDetail:
    item = queue_item(row)
    report = row.report
    lines = [{"line": line["line"], "item": line.get("item", ""), "vendor": line.get("vendor", ""),
              "category_label": line.get("category_label"), "amount_text": _money(int(line.get("amount_cents", 0))),
              "verdict": _line_verdict(line), "verdict_label": VERDICT_LABELS[Verdict(_line_verdict(line))]}
             for line in report.get("lines", [])]
    return ApplicationDetail(**item.model_dump(), fund_name=(report.get("fund") or {}).get("fund_name"), lines=lines,
                             reasons=reasons(report), denial_rule_ids=list(row.denial_rule_ids or []),
                             denial_draft=row.denial_draft, denial_approved_text=row.denial_approved_text,
                             denial_approved_by=row.denial_approved_by, notice=PRECHECK_NOTICE)


def failure_stats(rows: list[SentApplication], ruleset: RuleSet) -> FailureStats:
    """How many sent applications break each rule (red findings, counted once per application). Aggregate only: no
    club or event is named."""
    from app.rules import citation_for

    counter: Counter[str] = Counter()
    approved = 0
    for row in rows:
        counter.update({r.rule_id for r in reasons(row.report) if r.verdict is Verdict.RED})
        approved += row.denial_status == "approved"
    out = []
    for rule_id, count in sorted(counter.items(), key=lambda kv: (-kv[1], kv[0])):
        known = rule_id in ruleset
        out.append(FailureRow(rule_id=rule_id, title=ruleset.get(rule_id).title if known else rule_id, applications=count,
                              citation=citation_for(ruleset, rule_id) if known else None))
    return FailureStats(applications=len(rows), rows=out, approved_denials=approved,
                        note="Counts the applications clubs chose to send that break each rule, as Greenlight's pre-check "
                             "found it. It names no club and predicts no decision.")
