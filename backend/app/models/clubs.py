from __future__ import annotations

from datetime import date

from sqlalchemy import CheckConstraint, Date, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.models._base import TimestampMixin


class Club(TimestampMixin, Base):
    """A student organization. A club's data is private to the club (PROJECT_CONTEXT section 9)."""

    __tablename__ = "clubs"
    __table_args__ = (CheckConstraint("level IN ('undergraduate', 'graduate')", name="ck_clubs_level"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    purpose: Mapped[str | None] = mapped_column(Text)
    level: Mapped[str] = mapped_column(String(20), nullable=False, default="undergraduate")
    # Date first registered with Campus Activities; the Social and Recreation/Startup fund
    # covers clubs first registered within the last two academic semesters.
    first_registered_on: Mapped[date | None] = mapped_column(Date)


class User(TimestampMixin, Base):
    """A demo account. `role` is 'officer' (belongs to one club) or 'usg_reviewer'."""

    __tablename__ = "users"
    __table_args__ = (CheckConstraint("role IN ('officer', 'usg_reviewer')", name="ck_users_role"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(254), unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(200), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False, default="officer")
    club_id: Mapped[int | None] = mapped_column(ForeignKey("clubs.id", ondelete="SET NULL"))
