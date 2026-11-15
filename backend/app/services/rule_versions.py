from __future__ import annotations

import hashlib
import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import RuleVersion
from app.rules.loader import RuleSet


def sync_rule_versions(session: Session, ruleset: RuleSet) -> int:
    """Store a rule as its next version whenever its content differs from its latest stored version
    (including a change back to an earlier text). Returns how many versions were added."""
    added = 0
    for rule in ruleset:
        content = rule.model_dump(mode="json")
        digest = hashlib.sha256(json.dumps(content, sort_keys=True).encode("utf-8")).hexdigest()
        latest = session.scalars(
            select(RuleVersion).where(RuleVersion.rule_id == rule.id).order_by(RuleVersion.version.desc()).limit(1)
        ).first()
        if latest is not None and latest.content_sha256 == digest:
            continue
        session.add(
            RuleVersion(
                rule_id=rule.id,
                version=(latest.version if latest else 0) + 1,
                domain=rule.domain,
                content=content,
                content_sha256=digest,
            )
        )
        added += 1
    session.commit()
    return added
