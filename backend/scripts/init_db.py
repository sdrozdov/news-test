"""Create database tables from the ORM metadata.

Run once against a fresh database (e.g. in production where AUTO_CREATE_TABLES
is off):  python -m scripts.init_db
"""

from __future__ import annotations

import asyncio

from app.config import get_settings
from app.db.session import create_engine_and_factory, init_models

# Import models so their tables register on the metadata before create_all.
from app.models import Analysis, Article  # noqa: F401


async def main() -> None:
    settings = get_settings()
    engine, _ = create_engine_and_factory(settings)
    await init_models(engine)
    await engine.dispose()
    print("Database tables created.")


if __name__ == "__main__":
    asyncio.run(main())
