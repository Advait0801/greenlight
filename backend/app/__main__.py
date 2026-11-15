"""Start the backend: `python -m app` (from backend/).

Reads BACKEND_PORT and BACKEND_HOST from the shell or the repository's .env, like every other
setting, so a port set only in .env is honoured. Pass --no-reload to turn auto-reload off.
"""

from __future__ import annotations

import argparse

import uvicorn

from app.config import BACKEND_DIR, get_settings


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Greenlight backend.")
    parser.add_argument("--no-reload", action="store_true", help="do not restart on code changes")
    args = parser.parse_args()
    settings = get_settings()
    uvicorn.run(
        "app.main:app",
        host=settings.backend_host,
        port=settings.backend_port,
        reload=not args.no_reload,
        reload_dirs=[str(BACKEND_DIR / "app")],
    )


if __name__ == "__main__":
    main()
