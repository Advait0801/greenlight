from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import require_ruleset
from app.rules import RuleSet, citation_for
from app.rules.schema import Domain

router = APIRouter(prefix="/rules", tags=["rules"])


def _rule_out(ruleset: RuleSet, rule_id: str) -> dict[str, Any]:
    rule = ruleset.get(rule_id)
    return {
        **rule.model_dump(mode="json"),
        "display_severity": ruleset.display_severity(rule_id),
        "citation": citation_for(ruleset, rule_id).model_dump(mode="json"),
    }


@router.get("")
def list_rules(
    domain: Domain | None = Query(default=None, description="Only rules from this domain"),
    ruleset: RuleSet = Depends(require_ruleset),
) -> dict[str, Any]:
    rules = [_rule_out(ruleset, rule.id) for rule in ruleset if domain is None or rule.domain == domain]
    return {"count": len(rules), "rules": rules}


@router.get("/{rule_id}")
def get_rule(rule_id: str, ruleset: RuleSet = Depends(require_ruleset)) -> dict[str, Any]:
    if rule_id not in ruleset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"No rule with id '{rule_id}'.")
    return _rule_out(ruleset, rule_id)
