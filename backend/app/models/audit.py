from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.models._base import utcnow


class AuditLog(Base):
    """Every AI output and every human approval (PROJECT_CONTEXT section 5)."""

    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(primary_key=True)
    club_id: Mapped[int | None] = mapped_column(ForeignKey("clubs.id", ondelete="SET NULL"), index=True)
    actor: Mapped[str] = mapped_column(String(120), nullable=False)  # "ai:<model>" or "user:<id>"
    action: Mapped[str] = mapped_column(String(80), nullable=False)  # ai_output, approval, ...
    subject_type: Mapped[str | None] = mapped_column(String(80))
    subject_id: Mapped[str | None] = mapped_column(String(120))
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
