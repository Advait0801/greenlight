"""Test setup. Every test runs with AI_MODE=recorded and a throwaway SQLite database, so the suite
never calls the Claude API and never touches greenlight.db."""

from __future__ import annotations

import os
import shutil
import tempfile
from collections.abc import Iterator
from pathlib import Path

import pytest

_TMP = Path(tempfile.mkdtemp(prefix="greenlight-tests-"))
os.environ["AI_MODE"] = "recorded"
os.environ["DATABASE_URL"] = f"sqlite:///{_TMP / 'test.db'}"
os.environ["AI_RECORDINGS_DIR"] = str(_TMP / "recordings")
# Environment variables win over the developer's .env, so this keeps any real key out of the tests.
os.environ["ANTHROPIC_API_KEY"] = ""
os.environ.pop("RULES_DIR", None)

from app.config import REPO_ROOT, get_settings  # noqa: E402
from app.db import _session_factory, get_engine  # noqa: E402
from app.rules import get_calendar, get_ruleset  # noqa: E402

RULES_DIR = REPO_ROOT / "rules"


def clear_caches() -> None:
    for cached in (get_settings, get_engine, _session_factory, get_ruleset, get_calendar):
        cached.cache_clear()


@pytest.fixture
def rules_copy(tmp_path: Path) -> Path:
    """A private copy of rules/ (with snapshots) that a test may break."""
    target = tmp_path / "rules"
    shutil.copytree(RULES_DIR, target, ignore=shutil.ignore_patterns("raw"))
    return target


@pytest.fixture
def client() -> Iterator[object]:
    from fastapi.testclient import TestClient

    from app.main import create_app

    clear_caches()
    with TestClient(create_app()) as test_client:
        yield test_client
    clear_caches()


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    # `pytest tests/adversarial` must succeed before the breaker has added any tests there.
    if exitstatus == pytest.ExitCode.NO_TESTS_COLLECTED:
        args = [str(arg) for arg in session.config.args]
        if args and all("adversarial" in arg for arg in args):
            session.exitstatus = pytest.ExitCode.OK
    shutil.rmtree(_TMP, ignore_errors=True)
