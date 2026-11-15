"""Phase 6, iteration 2 (break): two users at once, slow AI service, the deployed site's file serving, start-up.

Each test states the behaviour the shipped site needs (PLAN.md Phase 6: the demo journey runs on the live link for
any visitor; one visitor must not stall another).
"""

from __future__ import annotations

import asyncio
import copy
import time
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import httpx
import pytest
from fastapi.testclient import TestClient

from tests.integration.test_money_api import BODY as CHECK

KEY = "break-passcode-phase6"
REVIEWER = {"X-Reviewer-Key": KEY}


# --------------------------------------------------------------------------------------------------------------
# A slow AI service: one visitor reading quotes must not freeze the site for everyone else.


def test_reading_a_quote_while_the_ai_service_is_slow_does_not_stall_other_visitors(monkeypatch: pytest.MonkeyPatch) -> None:
    """POST /money/read is an `async def` route that calls the (blocking) AI reader directly on the event loop, so
    while one visitor's quote waits on a slow Claude API (up to AI_TIMEOUT_SECONDS x 3 tries, per document, up to
    11 documents), every other request on the server - the demo journey included - waits too. The constitution
    check already moves its reader to a worker thread; the quote reader must do the same."""
    import app.api.money as money_api
    from app.main import create_app
    from app.services.quote_intake import IntakeError
    from tests.conftest import clear_caches

    def slow_reader(**_: Any) -> Any:
        time.sleep(1.5)  # stands in for a slow Claude API call
        raise IntakeError("Greenlight could not read 'pasted text' just now. Type its lines in instead.")

    monkeypatch.setattr(money_api, "read_quote", slow_reader)
    clear_caches()
    app = create_app()

    async def run() -> float:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            started = time.perf_counter()
            reading = asyncio.create_task(client.post("/money/read", data={"text": "Pizza Place: 20 pizzas, $300"}))
            await asyncio.sleep(0.1)  # the other visitor's request arrives 0.1 s later
            health = await client.get("/rules/usg-food-cap")
            waited = time.perf_counter() - started - 0.1
            assert health.status_code == 200
            await reading
            return waited

    waited = asyncio.run(run())
    clear_caches()
    assert waited < 0.75, f"another visitor's request waited {waited:.1f}s for a quote reading to finish"


# --------------------------------------------------------------------------------------------------------------
# Two USG reviewers at once.


@pytest.fixture
def usg(monkeypatch: pytest.MonkeyPatch, client: Any) -> Iterator[Any]:
    monkeypatch.setenv("USG_REVIEWER_KEY", KEY)
    from sqlalchemy import delete

    from app.config import get_settings
    from app.db import _session_factory
    from app.models import SentApplication

    get_settings.cache_clear()
    with _session_factory()() as session:
        session.execute(delete(SentApplication))
        session.commit()
    yield client
    monkeypatch.delenv("USG_REVIEWER_KEY")
    get_settings.cache_clear()


def _send(client: Any) -> dict[str, Any]:
    response = client.post("/usg/send", json={"club_name": "Lantern Cultural Society", "consent": True,
                                             "check": copy.deepcopy(CHECK)})
    assert response.status_code == 200, response.text
    return response.json()


def test_a_second_approval_cannot_replace_the_reason_the_club_already_reads(usg: Any) -> None:
    """Phase 5 iteration 3 stopped a new *draft* once a reason is approved, because the recorded reasons would then
    disagree with the text the club reads. A second *approval* (a second reviewer with the page still open, or a
    double submit after a slow response) still silently replaces the approved text the club already reads."""
    sent = _send(usg)
    app_id = usg.get("/usg/queue", headers=REVIEWER).json()["applications"][0]["id"]
    text = usg.post(f"/usg/applications/{app_id}/denial-draft", headers=REVIEWER,
                    json={"rule_ids": ["usg-food-cap"]}).json()["text"]
    first = usg.post(f"/usg/applications/{app_id}/denial-approve", headers=REVIEWER,
                     json={"text": text, "reviewer_name": "Reviewer A"})
    assert first.status_code == 200
    second = usg.post(f"/usg/applications/{app_id}/denial-approve", headers=REVIEWER,
                      json={"text": "Denied: DJ fees are not fundable.", "reviewer_name": "Reviewer B"})
    club_reads = usg.post(f"/usg/sent/{sent['reference']}", json={"club_token": sent["club_token"]}).json()
    assert second.status_code == 409
    assert club_reads["reviewer_message"] == text


# --------------------------------------------------------------------------------------------------------------
# The deployed site's file serving.


@pytest.fixture()
def site(tmp_path: Path) -> TestClient:
    from app.site import create_site

    dist = tmp_path / "dist"
    (dist / "assets").mkdir(parents=True)
    (dist / "index.html").write_text("<!doctype html><title>Greenlight</title><div id=root></div>")
    (dist / "assets" / "index-new.js").write_text("console.log('ok')")
    return TestClient(create_site(dist))


def test_a_missing_script_file_is_a_404_not_the_page(site: TestClient) -> None:
    """After a redeploy the hashed bundle name changes. A tab that loaded the old index.html asks for the old
    /assets/index-<hash>.js and gets index.html with status 200 and text/html, which the browser refuses as a module
    script: a blank page with no message. A missing file under /assets/ should be a plain 404."""
    with site:
        response = site.get("/assets/index-old.js")
        assert response.status_code == 404


# --------------------------------------------------------------------------------------------------------------
# Start-up: several processes against one fresh database (Replit autoscale starts more than one instance).


def test_tables_are_created_safely_when_several_processes_start_at_once(tmp_path: Path) -> None:
    """start.sh runs seed_demo.py (init_db) and the site's lifespan runs init_db again. On a fresh database, two
    instances starting together race in create_all: one fails with 'table ... already exists' (seen locally: 3 of 4
    concurrent seed runs failed). In the site's lifespan that failure stops the instance from starting."""
    import threading

    from sqlalchemy import create_engine

    from app.db import init_db

    url = f"sqlite:///{tmp_path / 'fresh.db'}"
    engines = [create_engine(url) for _ in range(6)]  # one engine per process that starts at the same moment
    start = threading.Barrier(len(engines))
    failures: list[str] = []

    def boot(engine: Any) -> None:
        start.wait()
        try:
            init_db(engine)
        except Exception as exc:  # noqa: BLE001 - any failure here stops an instance from starting
            failures.append(f"{type(exc).__name__}: {str(exc).splitlines()[0]}")

    threads = [threading.Thread(target=boot, args=(engine,)) for engine in engines]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=60)
    for engine in engines:
        engine.dispose()
    assert not failures, failures
