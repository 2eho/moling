"""Create all database tables synchronously.

Bypasses async/greenlet issues for local SQLite development.
"""

from __future__ import annotations

import os
import sys

# Load .env
_dotenv_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
if os.path.exists(_dotenv_path):
    try:
        from dotenv import load_dotenv
        load_dotenv(_dotenv_path)
    except ImportError:
        pass

# Use sync SQLite for table creation
# Must come BEFORE importing app.models (which may import from sqlalchemy)
DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite+aiosqlite:///./moling.db")

# Convert async SQLite URL to sync
if DATABASE_URL.startswith("sqlite+aiosqlite://"):
    SYNC_URL = DATABASE_URL.replace("sqlite+aiosqlite://", "sqlite:///", 1)
elif DATABASE_URL.startswith("postgresql+asyncpg://"):
    # Fallback: use psycopg2 or just sqlite
    SYNC_URL = "sqlite:///./moling.db"
else:
    SYNC_URL = DATABASE_URL.replace("+asyncpg", "").replace("+aiosqlite", "")

print(f"Using sync URL: {SYNC_URL}")

from sqlalchemy import create_engine
from app.models import Base

engine = create_engine(SYNC_URL, echo=True)
Base.metadata.create_all(engine)
print("✅ All tables created successfully.")
