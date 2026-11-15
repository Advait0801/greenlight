"""The deployed site: the API under /api and the built frontend (frontend/dist) everywhere else, on one address.

Run with `python -m app --site` after `npm run build` in frontend/. In development the Vite dev server does the
same job (it forwards /api to the API), so this module is used only when deployed.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.responses import Response
from starlette.staticfiles import StaticFiles
from starlette.types import Scope

from app.config import REPO_ROOT
from app.main import app as api
from app.main import lifespan

FRONTEND_DIST = REPO_ROOT / "frontend" / "dist"


class SinglePageApp(StaticFiles):
    """Static files, with index.html for any other path so that a page's own address (e.g. /money/check) loads."""

    async def get_response(self, path: str, scope: Scope) -> Response:
        try:
            return await super().get_response(path, scope)
        except StarletteHTTPException as exc:
            # A missing built file (e.g. an old bundle after a redeploy) is a plain 404, not the page (phase 6 iteration 2).
            if exc.status_code != 404 or path.startswith("assets/"):
                raise
            return await super().get_response("index.html", scope)


def create_site(dist: Path = FRONTEND_DIST) -> FastAPI:
    if not (dist / "index.html").is_file():
        raise RuntimeError(f"No built frontend in {dist}. Run `npm run build` in frontend/ first.")
    # The API's own startup (tables, rules, calendar) runs once, here: a mounted app's lifespan is not run.
    site = FastAPI(lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)
    site.mount("/api", api)
    site.mount("/", SinglePageApp(directory=dist, html=True), name="frontend")
    return site
