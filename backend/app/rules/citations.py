from __future__ import annotations

from typing import TYPE_CHECKING

from app.schemas.common import Citation, Finding, Verdict

if TYPE_CHECKING:
    from app.rules.loader import RuleSet


def citation_for(ruleset: RuleSet, rule_id: str) -> Citation:
    """The citation shown beside any finding or deadline produced from this rule."""
    rule = ruleset.get(rule_id)
    source = ruleset.source_for(rule)
    return Citation(
        rule_id=rule.id,
        source=rule.source,
        source_section=rule.source_section,
        source_url=rule.source_url,
        source_text=rule.source_text,
        effective_date=rule.effective_date,
        verified=rule.verified,
        snapshot_fetched_at=source.fetched_at,
        uncertain_reasons=ruleset.uncertain_reasons(rule_id),
        display_severity=ruleset.display_severity(rule_id),
    )


def finding_for(ruleset: RuleSet, rule_id: str, verdict: Verdict, message: str, fix: str | None = None) -> Finding:
    """The one way features build a finding: the citation comes from the rule table, and the Finding type
    refuses a green the rule cannot support."""
    return Finding(rule_id=rule_id, verdict=verdict, message=message, fix=fix, citation=citation_for(ruleset, rule_id))
