"""Types shared by every feature: verdicts, citations and findings."""

from __future__ import annotations

from datetime import date
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, model_validator

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
    # How the rule is shown: red, yellow, office_decides or info (yellow whenever it is uncertain).
    display_severity: str


class Finding(BaseModel):
    rule_id: str
    verdict: Verdict
    message: str
    fix: str | None
    citation: Citation

    @model_validator(mode="after")
    def _never_a_wrong_green(self) -> Finding:
        """Green only on a rule that is certain and not left to an office's judgment (CLAUDE.md)."""
        if self.citation.rule_id != self.rule_id:
            raise ValueError("the citation must be for the finding's own rule")
        if self.verdict is Verdict.GREEN:
            if self.citation.verified != "read" or self.citation.uncertain_reasons:
                raise ValueError(f"'{self.rule_id}' is not verified, so it cannot be green; use yellow")
            if self.citation.display_severity == "office_decides":
                raise ValueError(f"'{self.rule_id}' is decided by the office, so it cannot be green")
        return self
