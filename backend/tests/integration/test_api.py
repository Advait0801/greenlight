from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests.conftest import clear_caches


def test_health_reports_everything_loaded(client) -> None:  # type: ignore[no-untyped-def]
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["database"] == "ok"
    assert body["ai_mode"] == "recorded"
    assert body["rules"]["loaded"] and body["rules"]["count"] > 200
    from app.rules import load_rules
    from tests.conftest import RULES_DIR

    expected_unverified = sum(1 for rule in load_rules(RULES_DIR) if rule.verified == "unverified")
    assert body["rules"]["by_verification"]["unverified"] == expected_unverified >= 4
    assert body["calendar"]["verified"] == "read"  # confirmed by the user on 2026-11-14
    assert "pre-check, not a decision" in body["notice"]


def test_rules_carry_citations(client) -> None:  # type: ignore[no-untyped-def]
    body = client.get("/rules").json()
    assert body["count"] == len(body["rules"]) > 200
    for rule in body["rules"]:
        citation = rule["citation"]
        assert citation["source_url"].startswith("https://")
        assert citation["source_text"]
        assert citation["effective_date"]
        assert rule["display_severity"] != "green"


def test_unverified_rule_is_shown_yellow_with_its_reason(client) -> None:  # type: ignore[no-untyped-def]
    rule = client.get("/rules/usg-events-per-semester-cap").json()
    assert rule["severity"] == "red"
    assert rule["display_severity"] == "yellow"
    assert rule["citation"]["uncertain_reasons"]


def test_rules_filter_and_not_found(client) -> None:  # type: ignore[no-untyped-def]
    funding = client.get("/rules", params={"domain": "funding"}).json()
    assert funding["count"] > 0 and {r["domain"] for r in funding["rules"]} == {"funding"}
    assert client.get("/rules", params={"domain": "nonsense"}).status_code == 422
    assert client.get("/rules/no-such-rule").status_code == 404


def test_broken_rule_table_degrades_health_and_refuses_checks(rules_copy: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from fastapi.testclient import TestClient

    from app.main import create_app

    path = rules_copy / "funding.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    data["rules"][0].pop("source_text")
    path.write_text(json.dumps(data), encoding="utf-8")
    monkeypatch.setenv("RULES_DIR", str(rules_copy))
    clear_caches()
    try:
        with TestClient(create_app()) as broken:
            health = broken.get("/health")
            assert health.status_code == 503
            assert health.json()["status"] == "degraded"
            assert any("missing source_text" in p for p in health.json()["rules"]["problems"])
            refused = broken.get("/rules")
            assert refused.status_code == 503
            assert "no checks can run" in refused.json()["detail"]["message"]
    finally:
        monkeypatch.delenv("RULES_DIR")
        clear_caches()


def test_every_route_module_is_discovered() -> None:
    from app.api import discover_routers

    paths = {route.path for router in discover_routers() for route in router.routes}  # type: ignore[attr-defined]
    assert {"/health", "/rules", "/rules/{rule_id}"} <= paths


def test_health_shows_no_absolute_server_paths(rules_copy: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Regression (phase 0 iteration 2, L6)."""
    from fastapi.testclient import TestClient

    from app.config import REPO_ROOT
    from app.main import create_app

    (rules_copy / "sources" / "manifest.json").write_text("{not json", encoding="utf-8")
    monkeypatch.setenv("RULES_DIR", str(rules_copy))
    clear_caches()
    try:
        with TestClient(create_app()) as broken:
            text = broken.get("/health").text
            assert "manifest.json" in text
            assert str(rules_copy.parent) not in text
            assert str(REPO_ROOT) not in text
    finally:
        monkeypatch.delenv("RULES_DIR")
        clear_caches()


def test_health_degrades_when_calendar_and_rules_disagree(rules_copy: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Regression (phase 0 iteration 2, L5): the app, not only validate_rules.py, checks agreement."""
    from fastapi.testclient import TestClient

    from app.main import create_app

    path = rules_copy / "calendar.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    data["business_days"]["verified"] = "read"
    path.write_text(json.dumps(data), encoding="utf-8")
    monkeypatch.setenv("RULES_DIR", str(rules_copy))
    clear_caches()
    try:
        with TestClient(create_app()) as broken:
            health = broken.get("/health")
            assert health.status_code == 503
            assert any("must agree" in p for p in health.json()["rules"]["problems"])
    finally:
        monkeypatch.delenv("RULES_DIR")
        clear_caches()


def test_start_up_survives_another_worker_storing_the_same_rule_versions(monkeypatch: pytest.MonkeyPatch) -> None:
    """Regression (phase 0 iteration 2 L8; test added after iteration 3, code audit M): when two workers
    start at once, the second one's insert fails on the unique key; the app still starts."""
    from fastapi.testclient import TestClient
    from sqlalchemy.exc import IntegrityError

    import app.main as main

    def clash(*_args: object, **_kwargs: object) -> int:
        raise IntegrityError("INSERT INTO rule_versions", {}, Exception("UNIQUE constraint failed"))

    monkeypatch.setattr(main, "sync_rule_versions", clash)
    with TestClient(main.create_app()) as started:
        assert started.get("/health").status_code == 200
