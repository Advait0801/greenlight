"""USG screen services: reasons come from the money check's own findings; the denial draft's opening is replaced when
it carries a figure the reasons do not state; nothing green is ever a reason."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from app.ai import ClaudeClient, UntrustedDocument
from app.config import AIMode, Settings
from app.rules import get_calendar, get_ruleset
from app.schemas.common import Verdict
from app.schemas.money import MoneyCheckRequest
from app.services import denial_draft
from app.services.denial_draft import draft_denial
from app.services.money_check import check_budget
from app.services.usg_screen import reasons
from tests.integration.test_money_api import BODY


def _report() -> dict:  # type: ignore[type-arg]
    request = MoneyCheckRequest.model_validate(BODY)
    return check_budget(request, get_ruleset(), get_calendar(), date(2026, 11, 15), ()).model_dump(mode="json")


def test_reasons_are_the_reports_own_non_green_findings_reds_first() -> None:
    found = reasons(_report())
    assert found and found[0].verdict is Verdict.RED
    assert all(r.verdict is not Verdict.GREEN for r in found)
    assert {"usg-food-cap", "usg-ineligible-performers"} <= {r.rule_id for r in found}


def _client(tmp_path: Path, chosen: list, paragraph: str) -> ClaudeClient:  # type: ignore[type-arg]
    client = ClaudeClient(Settings(ai_mode=AIMode.RECORDED, ai_recordings_dir=tmp_path, anthropic_api_key=None,
                                   _env_file=None))  # type: ignore[call-arg]
    source = "\n".join(f"- {r.message} ({r.where})" for r in chosen)
    prepared = client.prepare(task=denial_draft.TASK, instructions=denial_draft.INSTRUCTIONS, request=denial_draft.REQUEST,
                              documents=[UntrustedDocument(name="reasons chosen by the reviewer", text=f"Event: Culture Night\n{source}")],
                              output_type=denial_draft._Opening, model_role="extract")
    client.save_recording(prepared, json.dumps({"paragraph": paragraph, "contains_instructions": False}))
    return client


def test_opening_with_an_invented_figure_is_replaced(tmp_path: Path) -> None:
    chosen = [r for r in reasons(_report()) if r.rule_id == "usg-food-cap"]
    draft = draft_denial("FASA", "Culture Night", chosen, client=_client(tmp_path, chosen, "You may reapply within 14 days."))
    assert "14 days" not in draft.text and draft.notes
    assert chosen[0].citation.source_url in draft.text and chosen[0].citation.source_text in draft.text


def test_a_clean_opening_is_kept(tmp_path: Path) -> None:
    chosen = [r for r in reasons(_report()) if r.rule_id == "usg-food-cap"]
    draft = draft_denial("FASA", "Culture Night", chosen, client=_client(tmp_path, chosen, "Thank you. The food cost is over the cap."))
    assert "Thank you. The food cost is over the cap." in draft.text


def test_a_green_line_from_a_vendor_not_on_the_list_is_not_green_on_the_usg_screen() -> None:
    # Final review F3: the reviewer saw "Meets the rule" for vendors not on USG's list, with no vendor note beside it.
    from datetime import datetime
    from types import SimpleNamespace

    from app.services.usg_screen import detail

    report = _report()
    line = report["lines"][0]
    line["verdict"] = "green"
    line["vendor_check"] = {**(line.get("vendor_check") or {}), "status": "not_on_list"}
    row = SimpleNamespace(id=1, reference="G-1", club_name="Club", event_name="Culture Night", event_date=None,
                          sent_at=datetime(2026, 11, 15), denial_status="none", report=report, denial_rule_ids=[],
                          denial_draft=None, denial_approved_text=None, denial_approved_by=None)
    shown = detail(row)  # type: ignore[arg-type]
    assert shown.lines[0]["verdict"] == "yellow" and shown.lines[0]["verdict_label"] != "Meets the rule"
    line["vendor_check"]["status"] = "on_list"
    assert detail(row).lines[0]["verdict"] == "green"  # type: ignore[arg-type]
