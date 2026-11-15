"""Settings, read from environment variables and the repository's `.env` file."""

from __future__ import annotations

from enum import StrEnum
from functools import lru_cache
from pathlib import Path

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_DIR.parent


class AIMode(StrEnum):
    """How the Claude client behaves.

    live      call the Claude API
    recorded  replay saved responses only; never touches the network (tests, demo fallback)
    record    call the Claude API and save each response for later replay
    """

    LIVE = "live"
    RECORDED = "recorded"
    RECORD = "record"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(REPO_ROOT / ".env", BACKEND_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: str = "dev"
    # A relative SQLite path is resolved against backend/, so the app, the scripts and the tests
    # agree on one file whatever directory they are started from.
    database_url: str = "sqlite:///./greenlight.db"

    # Ports (also read by the frontend's Vite config). `python -m app` uses backend_port.
    backend_host: str = "127.0.0.1"
    backend_port: int = Field(default=8000, ge=1, le=65535)
    frontend_port: int = Field(default=5173, ge=1, le=65535)

    # Claude. Model names come from the environment so they can change without a code change.
    ai_mode: AIMode = AIMode.RECORDED
    anthropic_api_key: SecretStr | None = None
    model_extract: str = "claude-sonnet-5-5"
    model_classify: str = "claude-haiku-5-5"
    ai_timeout_seconds: float = 60.0
    ai_recordings_dir: Path = REPO_ROOT / "data" / "ai_recordings"

    # Extra browser origins allowed to call the API directly (comma-separated). The dev server on
    # FRONTEND_PORT is always allowed; with the /api proxy, none is needed.
    frontend_origin: str = ""

    rules_dir: Path = REPO_ROOT / "rules"

    # The passcode a USG reviewer types to open the USG screen. Unset: the USG screen is closed (503).
    usg_reviewer_key: SecretStr | None = None

    @field_validator("database_url")
    @classmethod
    def _anchor_sqlite_path(cls, value: str) -> str:
        # Hosts such as Replit give a plain postgres:// or postgresql:// URL; SQLAlchemy needs the driver named.
        for prefix in ("postgres://", "postgresql://"):
            if value.startswith(prefix):
                return "postgresql+psycopg://" + value[len(prefix):]
        scheme, sep, rest = value.partition(":///")
        if not sep or not (scheme == "sqlite" or scheme.startswith("sqlite+")) or rest.startswith("/"):
            return value  # not SQLite, or already absolute (sqlite:////abs/path)
        if not rest or rest.startswith(":memory:") or rest.startswith("file:"):
            return value
        return f"{scheme}:///{(BACKEND_DIR / rest).resolve()}"

    @field_validator("rules_dir", "ai_recordings_dir")
    @classmethod
    def _anchor_folder(cls, value: Path) -> Path:
        """A relative folder is relative to the repository root, wherever the process starts."""
        return value if value.is_absolute() else (REPO_ROOT / value).resolve()

    @property
    def allowed_origins(self) -> list[str]:
        local = [f"http://localhost:{self.frontend_port}", f"http://127.0.0.1:{self.frontend_port}"]
        extra = [origin.strip() for origin in self.frontend_origin.split(",") if origin.strip()]
        return list(dict.fromkeys(local + extra))


@lru_cache
def get_settings() -> Settings:
    return Settings()
