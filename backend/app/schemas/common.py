"""Types shared by every feature: verdicts, citations and findings."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import date
from enum import StrEnum
from typing import Any

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
    # Rules from other sources that disagree with this one; a finding cites them too.
    conflicts_with: list[str] = []


class Finding(BaseModel):
    """One checked item. Frozen, and re-checked on every copy, so a verdict cannot be upgraded afterwards.
    Build findings with app.rules.finding_for, which takes the citation from the rule table."""

    model_config = ConfigDict(frozen=True)

    rule_id: str
    verdict: Verdict
    message: str
    fix: str | None
    citation: Citation

    def model_copy(self, *, update: Mapping[str, Any] | None = None, deep: bool = False) -> Finding:
        """A copy goes through the same checks as a new finding (pydantic's copy skips validation)."""
        copied = super().model_copy(update=update, deep=deep)
        return type(self).model_validate(copied.model_dump())

    @model_validator(mode="after")
    def _never_a_wrong_green(self) -> Finding:
        """Green only on a rule that is certain, gives a pass or fail, and is not left to an office's
        judgment (CLAUDE.md). For green, the citation must be the rule table's own, so a hand-built
        citation cannot claim a rule is verified."""
        if self.citation.rule_id != self.rule_id:
            raise ValueError("the citation must be for the finding's own rule")
        if self.verdict is Verdict.RED and self.citation.display_severity != "red":
            raise ValueError(
                f"'{self.rule_id}' is shown {self.citation.display_severity}, so it cannot be a certain red; "
                "use yellow (or office_decides)"
            )
        if self.verdict is Verdict.GREEN:
            from app.rules import citation_for, get_ruleset

            ruleset = get_ruleset()
            if self.citation != citation_for(ruleset, self.rule_id):
                raise ValueError(f"the citation for '{self.rule_id}' does not match the rule table, so it cannot be green")
            if self.citation.verified != "read" or self.citation.uncertain_reasons:
                raise ValueError(f"'{self.rule_id}' is not verified, so it cannot be green; use yellow")
            if self.citation.display_severity == "office_decides":
                raise ValueError(f"'{self.rule_id}' is decided by the office, so it cannot be green")
            if self.citation.display_severity != "red":
                raise ValueError(
                    f"'{self.rule_id}' is shown {self.citation.display_severity}, never a pass or fail, so it cannot be green"
                )
            stricter = ruleset.less_strict_side(self.rule_id)
            if stricter is not None:
                raise ValueError(
                    f"'{self.rule_id}' is the less strict side of a disagreement with '{stricter}'; check the stricter rule"
                )
        return self
