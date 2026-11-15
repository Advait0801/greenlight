"""Load the demo club from data/demo/ into the database selected by DATABASE_URL.

Usage (from the repository root, backend dependencies installed):

    python scripts/seed_demo.py

Safe to run more than once: the demo club this script created (same name, and every user one of
the demo users) and its demo users are replaced, so the result is always one copy of the demo data.
A club with the same name that the script did not create is never touched; the script stops instead.
"""

from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path
from typing import Any

from _common import DEMO_DIR, use_backend

use_backend()

from sqlalchemy import delete, select  # noqa: E402
from sqlalchemy.exc import IntegrityError  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from app.db import get_engine, init_db  # noqa: E402
from app.jsonutil import StrictJSONError, loads_strict  # noqa: E402
from app.models import Club, Event, User, YearPlan  # noqa: E402


def _date(value: str | None) -> date | None:
    return date.fromisoformat(value) if value else None


def seed(session: Session, demo: dict[str, Any]) -> dict[str, int]:
    club_data = demo["club"]
    demo_emails = {user["email"] for user in demo["users"]}
    existing = session.scalars(select(Club).where(Club.name == club_data["name"])).all()
    for club in existing:
        members = set(session.scalars(select(User.email).where(User.club_id == club.id)).all())
        # Only a club this script made (every user a demo user, and at least one) is replaced. A club with
        # the same name but other users, or with no users yet, is someone else's.
        if not members or members - demo_emails:
            raise SystemExit(
                f"A club named '{club.name}' that this script did not create already exists; refusing to replace it. "
                "Rename the demo club in data/demo/club.json or remove that club yourself."
            )
        plan_ids = session.scalars(select(YearPlan.id).where(YearPlan.club_id == club.id)).all()
        if plan_ids:
            session.execute(delete(Event).where(Event.plan_id.in_(plan_ids)))
            session.execute(delete(YearPlan).where(YearPlan.id.in_(plan_ids)))
        session.execute(delete(User).where(User.club_id == club.id))
        session.delete(club)
    emails = [user["email"] for user in demo["users"]]
    session.execute(delete(User).where(User.email.in_(emails)))
    session.flush()

    club = Club(
        name=club_data["name"],
        purpose=club_data["purpose"],
        level=club_data["level"],
        first_registered_on=_date(club_data.get("first_registered_on")),
    )
    session.add(club)
    session.flush()
    for user in demo["users"]:
        session.add(
            User(
                email=user["email"],
                display_name=user["display_name"],
                role=user["role"],
                club_id=club.id if user["role"] == "officer" else None,
            )
        )
    plan_data = demo["year_plan"]
    plan = YearPlan(
        club_id=club.id,
        period=plan_data["period"],
        money_on_hand_cents=plan_data["money_on_hand_cents"],
        expected_income_cents=plan_data["expected_income_cents"],
        unavailable_dates=plan_data.get("unavailable_dates", []),
    )
    session.add(plan)
    session.flush()
    for event in demo["events"]:
        session.add(
            Event(
                plan_id=plan.id,
                name=event["name"],
                event_date=_date(event["event_date"]),
                end_date=_date(event.get("end_date")),
                attributes=event.get("attributes", {}),
                estimated_cost_cents=event["estimated_cost_cents"],
            )
        )
    session.commit()
    return {"clubs": 1, "users": len(demo["users"]), "year_plans": 1, "events": len(demo["events"])}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Load the demo club into the database.")
    parser.add_argument("--file", type=Path, default=DEMO_DIR / "club.json")
    args = parser.parse_args(argv)
    try:
        demo = loads_strict(args.file.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, StrictJSONError) as exc:
        raise SystemExit(f"{args.file}: not a readable demo file ({exc})") from exc
    for event in demo.get("events", []) if isinstance(demo, dict) else []:
        start, end = event.get("event_date"), event.get("end_date")
        if start and end and end < start:
            raise SystemExit(f"{args.file}: event '{event.get('name')}' has end_date {end} before event_date {start}; nothing was seeded")
    init_db()
    with Session(get_engine()) as session:
        try:
            counts = seed(session, demo)
        except (KeyError, TypeError, ValueError) as exc:
            raise SystemExit(f"{args.file}: the demo data is incomplete or malformed ({exc!r}); nothing was seeded") from exc
        except IntegrityError as exc:
            raise SystemExit(f"{args.file}: the demo data breaks a database rule ({exc.orig}); nothing was seeded") from exc
    print("Seeded demo data: " + ", ".join(f"{count} {name}" for name, count in counts.items()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
