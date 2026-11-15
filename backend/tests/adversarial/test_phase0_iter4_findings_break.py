"""Phase 0, iteration 4 (break): the shared Finding and Citation types still allow a wrong green.

`Finding` is the one place meant to make "unsure is never green" impossible to break. It refuses
green on a rule that is unverified, office-decides or info, but not:
  - on a certain rule whose severity is yellow (the source hedges; some rules' own notes say
    "shown yellow, never green"),
  - on the less strict side of a pair of sources that disagree (PROJECT_CONTEXT 9: the stricter
    rule is applied and both are cited).
It also lets an unverified rule be shown as a certain red, and a citation for one side of a
conflict does not name the other side.
"""

from __future__ import annotations

import pytest

from app.rules import citation_for, finding_for, get_ruleset
from app.schemas.common import Verdict


@pytest.mark.parametrize(
    "rule_id",
    [
        "other-usc-funds-ask-usg",  # its notes: "Shown yellow, never green."
        "tes-space-request",  # "generally at least 3-6 weeks": "shown yellow rather than red"
        "usg-denial-other-university-funding",  # a possible denial reason, never a pass
    ],
)
def test_green_is_refused_on_a_rule_shown_yellow(rule_id: str) -> None:
    ruleset = get_ruleset()
    assert ruleset.display_severity(rule_id) == "yellow"
    with pytest.raises(ValueError):
        finding_for(ruleset, rule_id, Verdict.GREEN, "Meets the rule.")


@pytest.mark.parametrize(
    ("lenient", "stricter"),
    [
        # Decorations approval: FAQ 2 weeks, Terms and Conditions 3 weeks.
        ("tes-decorations-faq", "tes-decorations-terms"),
        # Travel: USG FAQ 8 calendar weeks, guidelines 9 academic weeks (unverified unit, so yellow).
        ("usg-faq-professional-travel-eight-weeks", "usg-deadline-travel"),
    ],
)
def test_green_is_refused_on_the_less_strict_side_of_a_source_conflict(lenient: str, stricter: str) -> None:
    """Decorations approved 16 days before the event meet the FAQ (2 weeks) and break the Terms
    (3 weeks). A feature that checks the FAQ rule and emits a green finding for it shows a pass
    that the stricter source denies; today the Finding type accepts it."""
    ruleset = get_ruleset()
    assert stricter in (ruleset.get(lenient).conflicts_with or [])
    with pytest.raises(ValueError):
        finding_for(ruleset, lenient, Verdict.GREEN, "Approved in time.")


@pytest.mark.parametrize("rule_id", ["usg-events-per-semester-cap", "usg-deadline-vendor"])
def test_red_is_refused_on_a_rule_that_is_not_certain(rule_id: str) -> None:
    """usg-events-per-semester-cap is unverified (only on the USG web page); usg-deadline-vendor
    counts undefined academic weeks. Both display yellow, but a red Finding citing them is accepted,
    which shows an unconfirmed rule as a certain failure ("unsure items go yellow")."""
    ruleset = get_ruleset()
    assert not ruleset.is_certain(rule_id)
    with pytest.raises(ValueError):
        finding_for(ruleset, rule_id, Verdict.RED, "Breaks the rule.")


def test_citation_of_one_side_of_a_conflict_names_the_other_side() -> None:
    """"Where official sources disagree, the stricter rule is applied and both are cited." A citation
    for the Terms' 3-week decorations rule carries nothing about the FAQ's 2-week rule, so a
    finding built from it cites one source only."""
    citation = citation_for(get_ruleset(), "tes-decorations-terms")
    assert "tes-decorations-faq" in citation.model_dump_json()
