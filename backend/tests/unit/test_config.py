"""Settings: ports and the database path read the same way from the shell or .env (phase 0 iteration 1, M1, M2, L1)."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.config import BACKEND_DIR, Settings


def test_relative_sqlite_path_is_anchored_to_backend() -> None:
    settings = Settings(_env_file=None, database_url="sqlite:///./greenlight.db")  # type: ignore[call-arg]
    assert settings.database_url == f"sqlite:///{BACKEND_DIR / 'greenlight.db'}"


@pytest.mark.parametrize("url", ["sqlite:////tmp/abs.db", "sqlite:///:memory:", "sqlite://", "postgresql://u@h/db"])
def test_other_database_urls_are_left_alone(url: str) -> None:
    assert Settings(_env_file=None, database_url=url).database_url == url  # type: ignore[call-arg]


def test_ports_come_from_the_env_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("BACKEND_PORT", raising=False)
    monkeypatch.delenv("FRONTEND_PORT", raising=False)
    env = tmp_path / ".env"
    env.write_text("BACKEND_PORT=8011\nFRONTEND_PORT=5186\n", encoding="utf-8")
    settings = Settings(_env_file=env)  # type: ignore[call-arg]
    assert (settings.backend_port, settings.frontend_port) == (8011, 5186)


def test_cors_allows_the_dev_server_on_frontend_port() -> None:
    settings = Settings(_env_file=None, frontend_port=5185, frontend_origin="https://greenlight.example")  # type: ignore[call-arg]
    assert settings.allowed_origins == ["http://localhost:5185", "http://127.0.0.1:5185", "https://greenlight.example"]


def test_bad_port_is_rejected() -> None:
    with pytest.raises(ValueError):
        Settings(_env_file=None, backend_port=70000)  # type: ignore[call-arg]


def test_relative_folders_and_driver_urls_are_anchored() -> None:
    """Regression (phase 0 iteration 2, L7)."""
    from app.config import REPO_ROOT

    settings = Settings(  # type: ignore[call-arg]
        _env_file=None, rules_dir="rules", ai_recordings_dir="data/ai_recordings", database_url="sqlite+pysqlite:///./x.db"
    )
    assert settings.rules_dir == REPO_ROOT / "rules"
    assert settings.ai_recordings_dir == REPO_ROOT / "data" / "ai_recordings"
    assert settings.database_url == f"sqlite+pysqlite:///{BACKEND_DIR / 'x.db'}"


def test_settings_read_the_repository_env_file() -> None:
    """Regression (phase 0 iteration 1 M1; test added after iteration 3, code audit M): the app's own
    settings name the repository's .env, so a port set only there is honoured by `python -m app`."""
    from app.config import REPO_ROOT

    env_files = Settings.model_config.get("env_file")
    assert env_files is not None and REPO_ROOT / ".env" in tuple(env_files)  # type: ignore[arg-type]
