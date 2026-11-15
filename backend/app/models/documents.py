from __future__ import annotations

from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.models._base import TimestampMixin, utcnow


class Document(Base):
    """An uploaded file. Its text is data, never instructions."""

    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(primary_key=True)
    club_id: Mapped[int] = mapped_column(ForeignKey("clubs.id", ondelete="CASCADE"), nullable=False, index=True)
    event_id: Mapped[int | None] = mapped_column(ForeignKey("events.id", ondelete="SET NULL"), index=True)
    kind: Mapped[str] = mapped_column(String(40), nullable=False)  # constitution, quote, cart_screenshot, ...
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str] = mapped_column(String(120), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    storage_path: Mapped[str | None] = mapped_column(String(500))
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class LineItem(TimestampMixin, Base):
    """A budget line extracted from a quote. `confidence` is the model's own rating, used only to
    decide when to ask a human; every figure is checked by code."""

    __tablename__ = "line_items"
    __table_args__ = (
        CheckConstraint("quantity >= 0", name="ck_line_items_quantity"),
        CheckConstraint("confidence IN ('high', 'medium', 'low')", name="ck_line_items_confidence"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    event_id: Mapped[int] = mapped_column(ForeignKey("events.id", ondelete="CASCADE"), nullable=False, index=True)
    document_id: Mapped[int | None] = mapped_column(ForeignKey("documents.id", ondelete="SET NULL"))
    vendor: Mapped[str | None] = mapped_column(String(200))
    item: Mapped[str] = mapped_column(String(300), nullable=False)
    amount_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    category: Mapped[str | None] = mapped_column(String(80))
    # The same three-level rating the AI layer returns (app.ai.schemas.Confidence); only "high" counts as
    # sure (app.ai.schemas.is_confident). Stored as the label, so no threshold can let "medium" through.
    confidence: Mapped[str] = mapped_column(String(6), nullable=False, default="low")
