"""Database engine and sessions. `DATABASE_URL` selects SQLite (local, tests) or Postgres (deployed)."""

from __future__ import annotations

from collections.abc import Iterator
from functools import lru_cache

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import get_settings


class Base(DeclarativeBase):
    pass


def make_engine(url: str) -> Engine:
    if url.startswith("sqlite"):
        engine = create_engine(url, connect_args={"check_same_thread": False})

        @event.listens_for(engine, "connect")
        def _enable_foreign_keys(dbapi_connection, _record) -> None:  # type: ignore[no-untyped-def]
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

        return engine
    return create_engine(url, pool_pre_ping=True)


@lru_cache
def get_engine() -> Engine:
    return make_engine(get_settings().database_url)


@lru_cache
def _session_factory() -> sessionmaker[Session]:
    return sessionmaker(bind=get_engine(), expire_on_commit=False)


def init_db(engine: Engine | None = None) -> None:
    """Create every table that does not exist yet. There are no migrations in this project:
    after a schema change, delete the local SQLite file and start again."""
    from app import models  # noqa: F401  (registers the tables on Base.metadata)

    Base.metadata.create_all(engine or get_engine())


def get_session() -> Iterator[Session]:
    """FastAPI dependency: one session per request."""
    session = _session_factory()()
    try:
        yield session
    finally:
        session.close()
