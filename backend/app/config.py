"""Settings, read from environment variables and the repository's `.env` file."""

from __future__ import annotations

from enum import StrEnum
from functools import lru_cache
from pathlib import Path

from pydantic import SecretStr
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
    database_url: str = "sqlite:///./greenlight.db"

    # Claude. Model names come from the environment so they can change without a code change.
    ai_mode: AIMode = AIMode.RECORDED
    anthropic_api_key: SecretStr | None = None
    model_extract: str = "claude-sonnet-5-5"
    model_classify: str = "claude-haiku-5-5"
    ai_timeout_seconds: float = 60.0
    ai_recordings_dir: Path = REPO_ROOT / "data" / "ai_recordings"

    # Comma-separated list of browser origins allowed to call the API directly.
    # The Vite dev server proxies /api to the backend, so local development does not need this.
    frontend_origin: str = "http://localhost:5173"

    rules_dir: Path = REPO_ROOT / "rules"

    @property
    def allowed_origins(self) -> list[str]:
        return [origin.strip() for origin in self.frontend_origin.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
