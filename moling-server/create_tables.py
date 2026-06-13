"""Create all database tables directly.

Used for local development with SQLite where Alembic migrations
may not be initialized yet.
"""

from __future__ import annotations

import asyncio
import os

# Load .env
_dotenv_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
if os.path.exists(_dotenv_path):
    try:
        from dotenv import load_dotenv
        load_dotenv(_dotenv_path)
    except ImportError:
        pass

from sqlalchemy.ext.asyncio import create_async_engine
from app.models import Base


async def create_tables() -> None:
    database_url = os.environ.get(
        "DATABASE_URL", "sqlite+aiosqlite:///./moling.db"
    )
    engine = create_async_engine(database_url, echo=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await engine.dispose()
    print("✅ All tables created successfully.")


if __name__ == "__main__":
    asyncio.run(create_tables())
