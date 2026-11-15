"""Start the backend: `python -m app` (from backend/).

Reads BACKEND_PORT and BACKEND_HOST from the shell or the repository's .env, like every other
setting, so a port set only in .env is honoured. Pass --no-reload to turn auto-reload off, and --site to
serve the built frontend and the API (under /api) on one address, as deployed.
"""

from __future__ import annotations

import argparse

import uvicorn

from app.config import BACKEND_DIR, get_settings


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Greenlight backend.")
    parser.add_argument("--no-reload", action="store_true", help="do not restart on code changes")
    parser.add_argument("--site", action="store_true",
                        help="serve frontend/dist and the API under /api on one address (deployment)")
    args = parser.parse_args()
    settings = get_settings()
    uvicorn.run(
        "app.site:create_site" if args.site else "app.main:app",
        factory=args.site,
        host=settings.backend_host,
        port=settings.backend_port,
        reload=not args.no_reload,
        reload_dirs=[str(BACKEND_DIR / "app")],
        proxy_headers=True,
    )


if __name__ == "__main__":
    main()
