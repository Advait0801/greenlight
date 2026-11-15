from __future__ import annotations

from datetime import date, datetime
from typing import Any

from sqlalchemy import JSON, CheckConstraint, Date, DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.models._base import utcnow


class SentApplication(Base):
    """A money check a club chose to send to the USG screen (PROJECT_CONTEXT 4I and section 9).

    Nothing reaches this table unless the club sends it with its consent. The club gets a secret token at that moment
    (only its hash is kept); with it the club can see its application and withdraw it. A denial reason is visible to
    the club only after a USG reviewer approved its text.
    """

    __tablename__ = "usg_sent_applications"
    __table_args__ = (
        CheckConstraint("status IN ('sent', 'withdrawn')", name="ck_usg_sent_status"),
        CheckConstraint("denial_status IN ('none', 'draft', 'approved')", name="ck_usg_sent_denial_status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    # Public reference the club quotes; not a secret.
    reference: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, index=True)
    club_token_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    club_name: Mapped[str] = mapped_column(String(200), nullable=False)
    event_name: Mapped[str] = mapped_column(String(200), nullable=False)
    event_date: Mapped[date | None] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(12), nullable=False, default="sent")
    # The checked budget as sent (no uploaded documents), and the code-only report Greenlight worked out from it.
    request: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    report: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    withdrawn_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    denial_status: Mapped[str] = mapped_column(String(12), nullable=False, default="none")
    denial_rule_ids: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    denial_draft: Mapped[str | None] = mapped_column(Text)
    denial_approved_text: Mapped[str | None] = mapped_column(Text)
    denial_approved_by: Mapped[str | None] = mapped_column(String(200))
    denial_approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
