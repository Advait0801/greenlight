"""Evaluator for the budget test set (Phase 3).

Each case is run end to end: the case's quote text is read by the quote reading step and its event description by
the fund reading step (AI_MODE=recorded replays saved answers), then the money check runs on the case's budget lines,
attachments and club figures with what was read.

caught           seeded violations found at their place (line or application) with at least their verdict
missed           seeded violations not found, plus every wrong green (a line expected non-green shown green)
wrongly_flagged  red or office-decides findings the test set does not expect, plus planted yellows shown as nothing

Also reported: exact totals and food per person, line verdicts, fund (matches or yellow), and draft allowed.
Extra yellow notes are allowed (data/eval/README.md, "Budgets: scoring notes").
"""

from __future__ import annotations

from datetime import date
from typing import Any

from app.config import get_settings
from app.rules import RuleSet, get_calendar
from app.schemas.money import BudgetEvent, BudgetLine, ClubMoney, MoneyCheckRequest, MoneyReport, QuoteDocument
from app.services.money_check import check_budget
from app.services.vendor_list import listed_vendors

AS_OF = date(2026, 11, 15)
RANK = {"green": 0, "yellow": 1, "office_decides": 2, "red": 3}


def _request(case: dict[str, Any], documents: list[QuoteDocument], reading: Any) -> MoneyCheckRequest:
    event = case["event"]
    return MoneyCheckRequest(
        event=BudgetEvent(name=event["name"], description=event["description"], event_date=event["event_date"],
                          end_date=event["end_date"], expected_attendance=event["expected_attendance"], venue=event["venue"],
                          ticketed=event["ticketed"], open_to_all_students=event["open_to_all_students"]),
        club=ClubMoney(**case["club"]), attachments=case["attachments"], lines=[BudgetLine(**line) for line in case["lines"]],
        documents=documents, fund_reading=reading, as_of=AS_OF,
    )


def _read(case: dict[str, Any], ruleset: RuleSet) -> tuple[list[QuoteDocument], Any, list[str]]:
    from app.services.fund_reading import FundReadingError, read_fund
    from app.services.quote_intake import IntakeError, read_quote

    errors: list[str] = []
    documents: list[QuoteDocument] = []
    try:
        documents.append(read_quote(index=1, name="quote", text=case["quote_text"], ruleset=ruleset).document)
    except IntakeError as exc:
        errors.append(f"quote: {exc}")
    reading = None
    try:
        reading = read_fund(case["event"]["name"], case["event"]["description"], ruleset=ruleset).reading
    except FundReadingError as exc:
        errors.append(f"fund: {exc}")
    return documents, reading, errors


def _findings(report: MoneyReport) -> dict[str, list[tuple[str | None, str, str]]]:
    """place -> [(rule_id, verdict, reason)]"""
    out: dict[str, list[tuple[str | None, str, str]]] = {}
    for line in report.lines:
        out[f"line {line.line}"] = [(f.finding.rule_id, f.finding.verdict.value, f.reason) for f in line.findings]
    out["application"] = [(f.finding.rule_id, f.finding.verdict.value, f.reason) for f in report.application]
    return out


def _has(got: list[tuple[str | None, str, str]], rule_id: str | None, verdict: str, reason: str) -> bool:
    for g_rule, g_verdict, g_reason in got:
        same = g_reason == reason if reason != "rule" else (g_rule == rule_id and g_reason == "rule")
        if same and RANK[g_verdict] >= RANK[verdict] and (verdict != "office_decides" or g_verdict == "office_decides"):
            return True
    return False


def compare(case: dict[str, Any], report: MoneyReport) -> dict[str, Any]:
    expected = case["expected"]
    got = _findings(report)
    want: dict[str, list[dict[str, Any]]] = {f"line {e['line']}": e["findings"] for e in expected["lines"]}
    want["application"] = expected["application"]
    missing: list[str] = []
    for place, findings in want.items():
        for f in findings:
            if not _has(got.get(place, []), f.get("rule_id"), f["verdict"], f.get("reason", "rule")):
                missing.append(f"{place}: {f.get('rule_id') or f.get('reason')} {f['verdict']}")
    extra: list[str] = []
    for place, findings in got.items():
        wanted = want.get(place, [])
        for rule_id, verdict, reason in findings:
            if verdict not in ("red", "office_decides"):
                continue
            if not any(w.get("rule_id") == rule_id and w["verdict"] == verdict for w in wanted):
                extra.append(f"{place}: {rule_id} {verdict}")
    caught, missed = 0, []
    for seeded in expected["seeded_violations"]:
        places = [p for p in want if any(f.get("rule_id") == seeded["rule_id"] for f in want[p])]
        ok = False
        for place in places:
            for f in want[place]:
                if f.get("rule_id") == seeded["rule_id"] and _has(got.get(place, []), f.get("rule_id"), f["verdict"], f.get("reason", "rule")):
                    ok = True
        if ok:
            caught += 1
        else:
            missed.append(f"{seeded['rule_id']} ({seeded['where']})")
    lines = {line.line: line.verdict.value for line in report.lines}
    wrong_greens = [e["line"] for e in expected["lines"] if e["verdict"] != "green" and lines.get(e["line"]) == "green"]
    line_diffs = [{"line": e["line"], "got": lines.get(e["line"]), "want": e["verdict"]} for e in expected["lines"]
                  if lines.get(e["line"]) != e["verdict"]]
    fund = report.fund
    fund_ok = fund.status == "unsure" or fund.fund == expected["expected_fund"]
    totals_ok = (report.totals.total_cents == expected["total_cents"]
                 and report.totals.food_per_person_cents == expected["food_per_person_cents"])
    return {
        "caught": caught, "missed": missed, "missing_findings": missing, "extra": extra, "wrong_greens": wrong_greens,
        "line_diffs": line_diffs, "fund": fund.fund, "fund_status": fund.status, "fund_ok": fund_ok,
        "totals_ok": totals_ok, "draft_ok": report.draft_allowed == expected["draft_allowed"],
    }


def evaluate(data: dict[str, Any], ruleset: RuleSet) -> dict[str, Any]:
    calendar = get_calendar()
    vendors = listed_vendors(ruleset, get_settings().rules_dir / "sources")
    rows = []
    for case in data["cases"]:
        documents, reading, errors = _read(case, ruleset)
        report = check_budget(_request(case, documents, reading), ruleset, calendar, AS_OF, vendors)
        rows.append({"id": case["id"], "errors": errors, **compare(case, report)})
    seeded = sum(len(case["expected"]["seeded_violations"]) for case in data["cases"])
    caught = sum(row["caught"] for row in rows)
    wrong_greens = sum(len(row["wrong_greens"]) for row in rows)
    missed = sum(len(row["missed"]) for row in rows) + wrong_greens
    wrongly = sum(len(row["extra"]) for row in rows)
    fund_ok = sum(1 for row in rows if row["fund_ok"])
    notes = (
        f"seeded violations caught {caught}/{seeded}; wrong greens {wrong_greens}; fund matches or yellow {fund_ok}/{len(rows)}; "
        f"totals exact {sum(1 for r in rows if r['totals_ok'])}/{len(rows)}; draft allowed right "
        f"{sum(1 for r in rows if r['draft_ok'])}/{len(rows)}; expected findings missing "
        f"{sum(len(r['missing_findings']) for r in rows)}; line verdicts differing {sum(len(r['line_diffs']) for r in rows)}; "
        f"reading errors {sum(len(r['errors']) for r in rows)}"
    )
    details = [row for row in rows if row["missed"] or row["missing_findings"] or row["extra"] or row["wrong_greens"]
               or row["line_diffs"] or not row["fund_ok"] or not row["totals_ok"] or not row["draft_ok"] or row["errors"]]
    return {"caught": caught, "missed": missed, "wrongly_flagged": wrongly, "details": details, "notes": notes}
