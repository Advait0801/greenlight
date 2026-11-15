from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.models._base import utcnow


class RuleVersion(Base):
    """Every version of every rule that has been loaded from rules/*.json.

    The JSON files are the source of truth; this table keeps history so that a changed rule
    can be shown old-beside-new (rule-change alerts) and so saved results can name the
    version they were checked against.
    """

    __tablename__ = "rules"
    __table_args__ = (UniqueConstraint("rule_id", "version", name="uq_rules_rule_version"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    rule_id: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    version: Mapped[int] = mapped_column(nullable=False)
    domain: Mapped[str] = mapped_column(String(40), nullable=False)
    content: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    content_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    loaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
