"""The recognition routes."""

from __future__ import annotations

from typing import Any

from app.config import REPO_ROOT

EVAL = REPO_ROOT / "data" / "eval" / "constitutions" / "texts"
CLEAN = (EVAL / "co-01.txt").read_text(encoding="utf-8")
FLAGS = {"has_parent_organization": "no", "has_school_affiliation": "no", "has_additional_officers": "yes",
         "has_appointed_positions": "yes"}


def test_pasted_text_is_checked(client: Any) -> None:
    response = client.post("/constitution/check", data={"text": CLEAN, **FLAGS})
    assert response.status_code == 200
    body = response.json()
    assert body["readable"] and body["notice"].startswith("Greenlight is a pre-check")
    assert body["summary"]["not_applicable"] == 5
    clause = body["clauses"][0]
    assert clause["citation"]["source_url"] and clause["template_text"] and clause["state_label"]


def test_uploaded_file_is_checked(client: Any) -> None:
    text = (EVAL / "co-10.txt").read_bytes()
    response = client.post("/constitution/check", files={"file": ("co-10.txt", text, "text/plain")}, data=FLAGS)
    body = response.json()
    assert response.status_code == 200 and body["overall"] == "red" and body["summary"]["missing"] == 4


def test_empty_file_is_not_a_pass(client: Any) -> None:
    response = client.post("/constitution/check", files={"file": ("empty.txt", b"", "text/plain")})
    body = response.json()
    assert response.status_code == 200 and body["readable"] is False and body["overall"] is None and body["message"]


def test_nothing_sent_is_not_a_pass(client: Any) -> None:
    body = client.post("/constitution/check", data={}).json()
    assert body["readable"] is False and body["overall"] is None


def test_file_and_text_together_are_refused(client: Any) -> None:
    response = client.post("/constitution/check", files={"file": ("a.txt", CLEAN.encode(), "text/plain")}, data={"text": CLEAN})
    assert response.status_code == 422


def test_bad_flag_is_refused(client: Any) -> None:
    assert client.post("/constitution/check", data={"text": CLEAN, "has_parent_organization": "maybe"}).status_code == 422


def test_injected_text_is_checked_normally(client: Any) -> None:
    body = client.post("/constitution/check", data={"text": (EVAL / "co-08.txt").read_text(encoding="utf-8"), **FLAGS}).json()
    assert body["overall"] == "red"
    assert "instruction_text" in {note["kind"] for note in body["notes"]}


def test_readiness_blank_and_ticked(client: Any) -> None:
    blank = client.get("/recognition/readiness", params={"as_of": "2026-11-15"}).json()
    assert blank["overall"] == "red" and len(blank["key_dates"]) == 3
    ticked = client.post("/recognition/readiness", params={"as_of": "2026-11-15"},
                         json={"constitution_ready": True, "advisor_named": True}).json()
    assert ticked["summary"]["done"] == 2


def test_readiness_refuses_unknown_fields(client: Any) -> None:
    assert client.post("/recognition/readiness", json={"approve_everything": True}).status_code == 422


def test_sample_constitution_runs_offline_and_finds_its_two_planted_problems(client: Any, monkeypatch: Any) -> None:
    """A fresh visitor can try the check without a file; the sample's AI reading is recorded, so it works offline."""
    from app.config import get_settings

    monkeypatch.setattr(get_settings(), "ai_recordings_dir", REPO_ROOT / "data" / "ai_recordings")
    sample = client.get("/constitution/demo").json()
    response = client.post("/constitution/check", data={"text": sample["text"], **sample["answers"]})
    assert response.status_code == 200
    states = {c["rule_id"]: c["state"] for c in response.json()["clauses"]}
    assert states["clause-ii-a-1"] == "contradicts"
    assert states["clause-iii-g-1"] == "missing"
