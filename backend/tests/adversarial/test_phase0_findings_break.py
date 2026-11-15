"""Phase 0, iteration 2 (break): the shared Finding type allows a wrong green.

CLAUDE.md: "When the model is unsure, the result is yellow. It never guesses green." and
"Rules where an office uses judgment are shown as 'the office decides', never as a pass."
Every later feature builds Finding objects from app/schemas/common.py. Today a green Finding
can cite an unverified rule, a rule resting on one, or an office-decides rule.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.rules import citation_for, load_rules
from app.schemas.common import Finding, Verdict
from tests.conftest import RULES_DIR


@pytest.fixture(scope="module")
def ruleset():  # type: ignore[no-untyped-def]
    return load_rules(RULES_DIR)


@pytest.mark.parametrize(
    "rule_id",
    [
        "usg-events-per-semester-cap",  # unverified (PROJECT_CONTEXT 7, "confirm before coding")
        "usg-deadline-vendor",  # read, but rests on the undefined academic week
        "dps-security",  # office_decides: DPS decides staffing and fees
    ],
)
def test_green_finding_cannot_cite_an_uncertain_or_discretionary_rule(ruleset, rule_id: str) -> None:  # type: ignore[no-untyped-def]
    with pytest.raises((ValidationError, ValueError)):
        Finding(
            rule_id=rule_id,
            verdict=Verdict.GREEN,
            message="Meets the rule",
            fix=None,
            citation=citation_for(ruleset, rule_id),
        )
