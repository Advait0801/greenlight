"""The shared Finding type: a green verdict needs a certain rule that gives a pass or fail."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.rules import citation_for, finding_for, load_rules
from app.schemas.common import Finding, Verdict
from tests.conftest import RULES_DIR


@pytest.fixture(scope="module")
def ruleset():  # type: ignore[no-untyped-def]
    return load_rules(RULES_DIR)


# ---- Regression (phase 0 iteration 3, code audit M): three ways round the guard, and green on info ----


def test_a_finding_cannot_be_upgraded_to_green_by_assignment(ruleset) -> None:  # type: ignore[no-untyped-def]
    finding = finding_for(ruleset, "usg-events-per-semester-cap", Verdict.YELLOW, "Check with USG")
    with pytest.raises(ValidationError):
        finding.verdict = Verdict.GREEN  # type: ignore[misc]


def test_a_copy_goes_through_the_guard(ruleset) -> None:  # type: ignore[no-untyped-def]
    finding = finding_for(ruleset, "dps-security", Verdict.OFFICE_DECIDES, "DPS decides")
    with pytest.raises(ValidationError):
        finding.model_copy(update={"verdict": Verdict.GREEN})


def test_a_hand_built_citation_cannot_claim_certainty(ruleset) -> None:  # type: ignore[no-untyped-def]
    forged = citation_for(ruleset, "usg-events-per-semester-cap").model_copy(
        update={"verified": "read", "uncertain_reasons": [], "display_severity": "red"}
    )
    with pytest.raises(ValidationError):
        Finding(rule_id="usg-events-per-semester-cap", verdict=Verdict.GREEN, message="ok", fix=None, citation=forged)


def test_an_information_rule_is_never_green(ruleset) -> None:  # type: ignore[no-untyped-def]
    info = next(rule.id for rule in ruleset if ruleset.display_severity(rule.id) == "info" and ruleset.is_certain(rule.id))
    with pytest.raises(ValidationError):
        Finding(rule_id=info, verdict=Verdict.GREEN, message="ok", fix=None, citation=citation_for(ruleset, info))


def test_a_certain_red_rule_can_still_be_green(ruleset) -> None:  # type: ignore[no-untyped-def]
    rule_id = next(rule.id for rule in ruleset if ruleset.display_severity(rule.id) == "red" and ruleset.is_certain(rule.id))
    assert finding_for(ruleset, rule_id, Verdict.GREEN, "Meets the rule").verdict is Verdict.GREEN
