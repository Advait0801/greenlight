from __future__ import annotations

from typing import TYPE_CHECKING

from app.schemas.common import Citation

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
    )
