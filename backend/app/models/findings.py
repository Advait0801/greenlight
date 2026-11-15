from __future__ import annotations

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.models._base import TimestampMixin


class Finding(TimestampMixin, Base):
    """A verdict from the rule engine (never from the model)."""

    __tablename__ = "findings"
    __table_args__ = (
        CheckConstraint(
            "verdict IN ('green', 'yellow', 'red', 'office_decides')",
            name="ck_findings_verdict",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    club_id: Mapped[int] = mapped_column(ForeignKey("clubs.id", ondelete="CASCADE"), nullable=False, index=True)
    event_id: Mapped[int | None] = mapped_column(ForeignKey("events.id", ondelete="CASCADE"), index=True)
    rule_id: Mapped[str] = mapped_column(String(120), nullable=False)
    target_type: Mapped[str] = mapped_column(String(40), nullable=False)  # line_item, event, constitution_clause, ...
    target_id: Mapped[str | None] = mapped_column(String(120))
    verdict: Mapped[str] = mapped_column(String(20), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    fix: Mapped[str | None] = mapped_column(Text)
    # Set only when the club chose to send this application to the USG screen.
    shared_with_usg: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class FundingOption(TimestampMixin, Base):
    __tablename__ = "funding_options"

    id: Mapped[int] = mapped_column(primary_key=True)
    event_id: Mapped[int] = mapped_column(ForeignKey("events.id", ondelete="CASCADE"), nullable=False, index=True)
    option_type: Mapped[str] = mapped_column(String(80), nullable=False)
    rule_id: Mapped[str] = mapped_column(String(120), nullable=False)
    amount_cents: Mapped[int | None] = mapped_column(Integer)
    draft_email: Mapped[str | None] = mapped_column(Text)
    # A person must approve every draft before it is used (nothing is ever sent by the app).
    draft_approved: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
