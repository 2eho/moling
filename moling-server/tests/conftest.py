"""墨灵 (Moling) — Pytest 配置 (Windows 兼容版).

Windows 上：自动 skip 所有需要数据库的测试（greenlet DLL 缺失）。
Linux / macOS 上：使用 aiosqlite 内存数据库正常运行。
"""

import sys
import platform
import types

# ---------------------------------------------------------------------------
# Windows: 阻止 greenlet 被导入（防止 DLL load 崩溃）
# ---------------------------------------------------------------------------
IS_WINDOWS = platform.system() == "Windows"

if IS_WINDOWS:
    _fake_gl = types.ModuleType("greenlet")
    _fake_gl.getcurrent = lambda: None
    _fake_gl.greenlet = type("greenlet", (), {"spawn": lambda self, fn, *a, **k: None})
    _fake_gl.error = type("error", (Exception,), {})
    sys.modules["greenlet"] = _fake_gl

# ---------------------------------------------------------------------------
# 现在安全导入
# ---------------------------------------------------------------------------
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.dependencies import get_db, get_current_user, get_optional_user


# ---------------------------------------------------------------------------
# Windows: 自动 skip所有需要数据库的测试
# ---------------------------------------------------------------------------

def pytest_collection_modifyitems(config, items):
    """Windows 上 skip 任何引用了 client / async_client / test_db 等 fixture 的测试。"""
    if not IS_WINDOWS:
        return
    skip_reason = "Windows: 跳过数据库测试（greenlet DLL 不可用）"
    db_fixtures = {"client", "async_client", "test_db", "test_user", "auth_headers", "test_project"}
    for item in items:
        fixturenames = getattr(item, "fixturenames", [])
        if db_fixtures & set(fixturenames):
            item.add_marker(pytest.mark.skip(reason=skip_reason))


# ---------------------------------------------------------------------------
# 非数据库测试的 fixture（Windows / Linux 通用）
# ---------------------------------------------------------------------------

@pytest.fixture()
def client():
    """FastAPI TestClient（不覆盖 DB 依赖，用于不需要 DB 的测试）。"""
    with TestClient(app) as c:
        yield c


# ---------------------------------------------------------------------------
# Linux / macOS: 真实 DB fixtures（Windows 上不会被执行）
# ---------------------------------------------------------------------------

if not IS_WINDOWS:
    import asyncio
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

    TEST_DATABASE_URL = "sqlite+aiosqlite://"

    @pytest.fixture(scope="session")
    def event_loop():
        loop = asyncio.new_event_loop()
        yield loop
        loop.close()

    @pytest_asyncio.fixture
    async def test_db():
        engine = create_async_engine(TEST_DATABASE_URL, echo=False)
        from app.models.base import Base
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        session_factory = async_sessionmaker(engine, expire_on_commit=False)
        async with session_factory() as session:
            yield session
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        await engine.dispose()

    @pytest_asyncio.fixture
    async def async_client(test_db):
        from app.dependencies import get_db
        from httpx import AsyncClient, ASGITransport
        async def override_get_db():
            yield test_db
        app.dependency_overrides[get_db] = override_get_db
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            yield client
        app.dependency_overrides.clear()
