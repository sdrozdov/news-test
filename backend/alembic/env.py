"""Alembic environment.

Runs migrations against the app's async engine, with the target schema taken from
the ORM metadata so ``--autogenerate`` diffs against the models. The project only
runs online (``alembic upgrade head``), so there's no offline/SQL branch.
"""

from __future__ import annotations

import asyncio
from logging.config import fileConfig

import app.models  # noqa: F401 — importing the package registers every table on the metadata
from alembic import context
from app.config import get_settings
from app.db.base import Base
from app.db.session import create_engine_and_factory

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def _run_migrations(connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)
    with context.begin_transaction():
        context.run_migrations()


async def _migrate() -> None:
    engine, _ = create_engine_and_factory(get_settings())
    async with engine.connect() as connection:
        await connection.run_sync(_run_migrations)
    await engine.dispose()


asyncio.run(_migrate())
