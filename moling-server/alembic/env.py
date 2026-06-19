"""墨灵 (Moling) — Alembic Environment Configuration."""

from __future__ import annotations

import os
import sys
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

# ---- Load .env file ----
# Load .env before anything else so DATABASE_URL is available
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_dotenv_path = os.path.join(_project_root, ".env")
if os.path.exists(_dotenv_path):
    try:
        from dotenv import load_dotenv
        load_dotenv(_dotenv_path)
    except ImportError:
        pass

# ---- Alembic Config ----
config = context.config

# ---- Logging ----
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# ---- Override sqlalchemy.url from environment variable ----
DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "sqlite+aiosqlite:///./moling.db",
)

# Convert async SQLite URL to sync for Alembic
# Alembic needs a sync engine; replace aiosqlite with sync sqlite driver
if DATABASE_URL.startswith("sqlite+aiosqlite://"):
    SQLALCHEMY_URL = DATABASE_URL.replace("sqlite+aiosqlite://", "sqlite://", 1)
elif "+asyncpg" in DATABASE_URL:
    SQLALCHEMY_URL = DATABASE_URL.replace("+asyncpg", "+psycopg")
else:
    SQLALCHEMY_URL = DATABASE_URL

config.set_main_option("sqlalchemy.url", SQLALCHEMY_URL)

# ---- Import all models so Alembic can detect them ----
from app.models import Base  # noqa: E402

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )

        with context.begin_transaction():
            context.run_migrations()

    connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
