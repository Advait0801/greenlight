from __future__ import annotations

from datetime import date
from typing import Any

from sqlalchemy import JSON, CheckConstraint, Date, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.models._base import TimestampMixin


class YearPlan(TimestampMixin, Base):
    __tablename__ = "year_plans"
    __table_args__ = (
        CheckConstraint("money_on_hand_cents >= 0", name="ck_year_plans_money_on_hand"),
        CheckConstraint("expected_income_cents >= 0", name="ck_year_plans_expected_income"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    club_id: Mapped[int] = mapped_column(ForeignKey("clubs.id", ondelete="CASCADE"), nullable=False, index=True)
    period: Mapped[str] = mapped_column(String(40), nullable=False)  # e.g. "spring-2027" or "2026-27"
    money_on_hand_cents: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    expected_income_cents: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # Dates the officers are unavailable, as ISO date strings or {"start", "end"} ranges.
    unavailable_dates: Mapped[list[Any]] = mapped_column(JSON, nullable=False, default=list)


class Event(TimestampMixin, Base):
    __tablename__ = "events"
    __table_args__ = (CheckConstraint("estimated_cost_cents >= 0", name="ck_events_cost"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    plan_id: Mapped[int] = mapped_column(ForeignKey("year_plans.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    event_date: Mapped[date | None] = mapped_column(Date)
    end_date: Mapped[date | None] = mapped_column(Date)
    # Event attributes from PROJECT_CONTEXT section 4C (venue type, headcount, food, ...).
    attributes: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    estimated_cost_cents: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    funding_target: Mapped[str | None] = mapped_column(String(80))  # a fund rule id, or null
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="draft")


class Obligation(TimestampMixin, Base):
    """A form, approval or deadline an event needs. Dates come from the deadline calculator only."""

    __tablename__ = "obligations"

    id: Mapped[int] = mapped_column(primary_key=True)
    event_id: Mapped[int] = mapped_column(ForeignKey("events.id", ondelete="CASCADE"), nullable=False, index=True)
    rule_id: Mapped[str] = mapped_column(String(120), nullable=False)
    due_date: Mapped[date | None] = mapped_column(Date)
    owner_office: Mapped[str] = mapped_column(String(200), nullable=False)
    form_link: Mapped[str | None] = mapped_column(String(500))
    state: Mapped[str] = mapped_column(String(40), nullable=False, default="to_do")
