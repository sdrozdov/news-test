"""Database engine, session factory, and the request-scoped session dependency.

The engine is created from :class:`Settings` and attached to ``app.state`` in the
application factory, so tests can spin up an isolated (SQLite) engine without any
global mutation. ``get_session`` reads the factory off the running app.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from fastapi import Request
from sqlalchemy import event
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool, StaticPool

from app.config import Settings
from app.db.base import Base


def _normalize_pg_url(url: str) -> tuple[str, dict]:
    """Return ``(sqlalchemy_url, connect_args)`` for a Postgres URL.

    - Upgrades ``postgres(ql)://`` to the async ``postgresql+asyncpg`` driver.
    - Moves libpq-only query params (``sslmode``, ``channel_binding``) that
      asyncpg does not understand out of the URL and into ``connect_args``.
    """
    parts = urlsplit(url)
    scheme = parts.scheme
    if scheme in ("postgres", "postgresql"):
        scheme = "postgresql+asyncpg"

    connect_args: dict = {}
    query = dict(parse_qsl(parts.query))
    sslmode = query.pop("sslmode", None)
    query.pop("channel_binding", None)  # not supported by asyncpg
    # Only force SSL for modes that require it. `prefer`/`allow` keep libpq's
    # negotiate-then-fallback semantics, which asyncpg does by default.
    if sslmode in ("require", "verify-ca", "verify-full"):
        connect_args["ssl"] = True

    new_url = urlunsplit((scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))
    return new_url, connect_args


def create_engine_and_factory(
    settings: Settings,
) -> tuple[AsyncEngine, async_sessionmaker[AsyncSession]]:
    """Build an async engine + session factory for the given settings.

    Handles both Postgres (production/local docker) and SQLite (tests).
    """
    url = settings.database_url
    kwargs: dict = {"echo": settings.db_echo, "future": True}
    connect_args: dict = {}

    is_sqlite = url.startswith("sqlite")
    if is_sqlite:
        # In-memory SQLite for tests: keep a single shared connection alive.
        connect_args["check_same_thread"] = False
        kwargs["poolclass"] = StaticPool
    else:
        url, connect_args = _normalize_pg_url(url)
        if settings.db_use_null_pool:
            kwargs["poolclass"] = NullPool
        else:
            kwargs["pool_pre_ping"] = True

    engine = create_async_engine(url, connect_args=connect_args, **kwargs)

    if is_sqlite:
        # SQLite disables foreign-key enforcement by default; turn it on so
        # constraint behaviour matches Postgres.
        @event.listens_for(engine.sync_engine, "connect")
        def _enable_sqlite_fk(dbapi_conn, _record):  # pragma: no cover - trivial
            cursor = dbapi_conn.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    return engine, factory


async def init_models(engine: AsyncEngine) -> None:
    """Create tables from the ORM metadata (idempotent)."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_session(request: Request) -> AsyncIterator[AsyncSession]:
    """FastAPI dependency yielding a request-scoped session."""
    factory: async_sessionmaker[AsyncSession] = request.app.state.session_factory
    async with factory() as session:
        yield session
