from __future__ import annotations

import hashlib
import json

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import RuleVersion
from app.rules.loader import RuleSet


def sync_rule_versions(session: Session, ruleset: RuleSet) -> int:
    """Store any rule whose content is new as the next version of that rule. Returns how many were added."""
    added = 0
    for rule in ruleset:
        content = rule.model_dump(mode="json")
        digest = hashlib.sha256(json.dumps(content, sort_keys=True).encode("utf-8")).hexdigest()
        exists = session.scalar(
            select(RuleVersion.id).where(RuleVersion.rule_id == rule.id, RuleVersion.content_sha256 == digest)
        )
        if exists is not None:
            continue
        latest = session.scalar(select(func.max(RuleVersion.version)).where(RuleVersion.rule_id == rule.id)) or 0
        session.add(
            RuleVersion(
                rule_id=rule.id,
                version=latest + 1,
                domain=rule.domain,
                content=content,
                content_sha256=digest,
            )
        )
        added += 1
    session.commit()
    return added
