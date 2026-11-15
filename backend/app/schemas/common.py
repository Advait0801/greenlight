"""Types shared by every feature: verdicts, citations and findings."""

from __future__ import annotations

from datetime import date
from enum import StrEnum

from pydantic import BaseModel, ConfigDict

# Shown on every report (PROJECT_CONTEXT section 9).
PRECHECK_NOTICE = (
    "Greenlight is a pre-check, not a decision. The office that owns each rule makes the decision."
)


class Verdict(StrEnum):
    """A verdict on one checked item. Always shown with an icon and a text label, never colour alone."""

    GREEN = "green"
    YELLOW = "yellow"
    RED = "red"
    OFFICE_DECIDES = "office_decides"


VERDICT_LABELS: dict[Verdict, str] = {
    Verdict.GREEN: "Meets the rule",
    Verdict.YELLOW: "Needs a human look",
    Verdict.RED: "Breaks the rule",
    Verdict.OFFICE_DECIDES: "The office decides",
}


class Citation(BaseModel):
    """Where a finding or deadline comes from. Every finding and deadline carries one."""

    model_config = ConfigDict(frozen=True)

    rule_id: str
    source: str
    source_section: str | None
    source_url: str
    source_text: str
    effective_date: date
    verified: str
    snapshot_fetched_at: str | None
    uncertain_reasons: list[str]


class Finding(BaseModel):
    rule_id: str
    verdict: Verdict
    message: str
    fix: str | None
    citation: Citation
