"""Phase 0, iteration 2 (break): database constraints and rule-version history."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db import init_db, make_engine
from app.models import Club, Event, RuleVersion, YearPlan
from app.rules import load_rules
from app.services.rule_versions import sync_rule_versions
from tests.conftest import RULES_DIR


@pytest.fixture
def engine(tmp_path: Path):  # type: ignore[no-untyped-def]
    engine = make_engine(f"sqlite:///{tmp_path / 'db.sqlite'}")
    init_db(engine)
    yield engine
    engine.dispose()


def test_event_cannot_end_before_it_starts(engine) -> None:  # type: ignore[no-untyped-def]
    """Deadlines anchor on the first and last day (event_date, event_end_date). An event stored as
    ending two days before it starts gives the post-event deadlines a date before the event.
    The test sets refuse end_date < event_date; the events table accepts it."""
    with Session(engine) as session:
        club = Club(name="Date Club", level="undergraduate")
        session.add(club)
        session.flush()
        plan = YearPlan(club_id=club.id, period="spring-2027")
        session.add(plan)
        session.flush()
        session.add(Event(plan_id=plan.id, name="Retreat", event_date=date(2027, 3, 6), end_date=date(2027, 3, 4)))
        with pytest.raises(IntegrityError):
            session.flush()


def test_reverting_a_rule_makes_the_reverted_text_the_latest_version(engine) -> None:  # type: ignore[no-untyped-def]
    """The rules table keeps history 'so saved results can name the version they were checked
    against' and so a changed rule can be shown old beside new. Load the real rule, then a typo
    ($53), then the real rule again: today the third load adds nothing (its hash already exists),
    so the newest version on record is the typo while the app is checking against $35."""
    ruleset = load_rules(RULES_DIR)
    original = ruleset.get("usg-food-cap")
    with Session(engine) as session:
        sync_rule_versions(session, ruleset)
        ruleset.rules["usg-food-cap"] = original.model_copy(update={"message": "Food is capped at $53 per person."})
        sync_rule_versions(session, ruleset)
        ruleset.rules["usg-food-cap"] = original
        sync_rule_versions(session, ruleset)
        latest = session.scalars(
            select(RuleVersion).where(RuleVersion.rule_id == "usg-food-cap").order_by(RuleVersion.version.desc())
        ).first()
        assert latest is not None
        assert latest.content["message"] == original.message
