from __future__ import annotations

import json
from pathlib import Path

import pytest
from sqlalchemy import inspect, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.ai import AIResult
from app.ai.audit import log_ai_output
from app.config import AIMode
from app.db import Base, init_db, make_engine
from app.models import AuditLog, Club, Event, RuleVersion, YearPlan
from app.rules import load_rules
from app.services.rule_versions import sync_rule_versions
from tests.conftest import RULES_DIR

SECTION_5_TABLES = {
    "rules", "clubs", "users", "year_plans", "events", "obligations", "documents",
    "line_items", "findings", "funding_options", "audit_log",
}


@pytest.fixture
def engine(tmp_path: Path):  # type: ignore[no-untyped-def]
    engine = make_engine(f"sqlite:///{tmp_path / 'db.sqlite'}")
    init_db(engine)
    yield engine
    engine.dispose()


def test_every_table_from_section_5_exists(engine) -> None:  # type: ignore[no-untyped-def]
    assert SECTION_5_TABLES <= set(inspect(engine).get_table_names())
    assert SECTION_5_TABLES == set(Base.metadata.tables)


def test_money_is_stored_in_whole_cents_and_cannot_be_negative(engine) -> None:  # type: ignore[no-untyped-def]
    columns = {c["name"]: c for c in inspect(engine).get_columns("year_plans")}
    assert str(columns["money_on_hand_cents"]["type"]) == "INTEGER"
    with Session(engine) as session:
        club = Club(name="Test Club", level="undergraduate")
        session.add(club)
        session.flush()
        session.add(YearPlan(club_id=club.id, period="spring-2027", money_on_hand_cents=-1))
        with pytest.raises(IntegrityError):
            session.flush()


def test_deleting_a_club_removes_its_plans_and_events(engine) -> None:  # type: ignore[no-untyped-def]
    with Session(engine) as session:
        club = Club(name="Cascade Club", level="undergraduate")
        session.add(club)
        session.flush()
        plan = YearPlan(club_id=club.id, period="spring-2027")
        session.add(plan)
        session.flush()
        session.add(Event(plan_id=plan.id, name="Mixer"))
        session.commit()
        session.delete(club)
        session.commit()
        assert session.scalars(select(Event)).all() == []


def test_rule_versions_are_stored_once_and_versioned_on_change(engine) -> None:  # type: ignore[no-untyped-def]
    ruleset = load_rules(RULES_DIR)
    with Session(engine) as session:
        assert sync_rule_versions(session, ruleset) == len(ruleset)
        assert sync_rule_versions(session, ruleset) == 0
        rule = ruleset.get("usg-food-cap")
        changed = rule.model_copy(update={"message": "Food is capped at $35 per person (reworded)."})
        ruleset.rules["usg-food-cap"] = changed
        assert sync_rule_versions(session, ruleset) == 1
        versions = session.scalars(select(RuleVersion.version).where(RuleVersion.rule_id == "usg-food-cap")).all()
        assert sorted(versions) == [1, 2]


def test_ai_outputs_go_to_the_audit_log(engine) -> None:  # type: ignore[no-untyped-def]
    result = AIResult(output=None, task="selftest", model="claude-sonnet-5-5", mode=AIMode.RECORDED,
                      request_key="k" * 64, raw_text=json.dumps({"name": "x"}), stop_reason="end_turn")
    with Session(engine) as session:
        log_ai_output(session, result, club_id=None, subject_type="event", subject_id="1")
        session.commit()
        entry = session.scalars(select(AuditLog)).one()
        assert entry.actor == "ai:claude-sonnet-5-5"
        assert entry.payload["output"] == {"name": "x"}


@pytest.mark.parametrize(("confidence", "accepted"), [("high", True), ("medium", True), ("0.9", False)])
def test_line_item_confidence_is_the_ai_label(engine, confidence: str, accepted: bool) -> None:  # type: ignore[no-untyped-def]
    """Regression (phase 0 iteration 3, code audit L): the database and the AI layer use one confidence
    scale, so no float threshold can let 'medium' count as sure."""
    from datetime import date

    from app.models import LineItem

    with Session(engine) as session:
        club = Club(name="Test Club", level="undergraduate")
        session.add(club)
        session.flush()
        plan = YearPlan(club_id=club.id, period="spring-2027", money_on_hand_cents=0)
        session.add(plan)
        session.flush()
        event = Event(plan_id=plan.id, name="Night", event_date=date(2027, 2, 1), estimated_cost_cents=0)
        session.add(event)
        session.flush()
        session.add(LineItem(event_id=event.id, item="Pizza", amount_cents=100, confidence=confidence))
        if accepted:
            session.flush()
        else:
            with pytest.raises(IntegrityError):
                session.flush()
