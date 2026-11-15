"""Greenlight API.

Run from backend/:  uvicorn app.main:app --reload --port ${BACKEND_PORT:-8000}
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api import discover_routers
from app.config import get_settings
from app.db import get_engine, init_db
from app.rules import CalendarLoadError, RuleLoadError, get_calendar, get_ruleset
from app.services.rule_versions import sync_rule_versions

logger = logging.getLogger("greenlight")


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    init_db()
    try:
        ruleset = get_ruleset()
    except RuleLoadError as exc:
        # Start anyway so /health can explain the problem; every check route answers 503.
        logger.error("%s", exc)
    else:
        try:
            with Session(get_engine()) as session:
                added = sync_rule_versions(session, ruleset)
        except IntegrityError:
            # Another worker stored the same versions at the same moment; nothing is lost.
            added = 0
        logger.info("Loaded %d rules (%d new versions stored).", len(ruleset), added)
    try:
        get_calendar()
    except CalendarLoadError as exc:
        logger.error("%s", exc)
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="Greenlight",
        description="Pre-check and planning for USC student organization paperwork. A pre-check, not a decision.",
        version="0.1.0",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_methods=["GET", "POST", "PATCH", "DELETE"],
        allow_headers=["Content-Type"],
    )
    for router in discover_routers():
        app.include_router(router)
    return app


app = create_app()
