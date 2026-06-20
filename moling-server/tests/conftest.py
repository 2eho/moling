"""墨灵 (Moling) — Pytest 配置。

提供测试固件：测试数据库、认证头、测试项目等。
"""

import sys
import platform
import pytest
import asyncio
from typing import AsyncGenerator, Dict, Any

# ---------------------------------------------------------------------------
# Windows 兼容处理
# ---------------------------------------------------------------------------
IS_WINDOWS = platform.system() == "Windows"

if IS_WINDOWS:
    # 阻止 greenlet 被导入
    _fake_gl = type(sys)("greenlet")
    _fake_gl.getcurrent = lambda: None
    _fake_gl.greenlet = type("greenlet", (), {"spawn": lambda self, fn, *a, **k: None})
    _fake_gl.error = type("error", (Exception,), {})
    sys.modules["greenlet"] = _fake_gl

# ---------------------------------------------------------------------------
# 导入
# ---------------------------------------------------------------------------
from fastapi.testclient import TestClient
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.config import get_settings
from app.dependencies import get_db, get_current_user, get_optional_user
from app.models.base import Base

# ---------------------------------------------------------------------------
# Windows: 自动 skip 数据库测试
# ---------------------------------------------------------------------------

def pytest_collection_modifyitems(config, items):
    """Windows 上跳过需要数据库的测试。"""
    if not IS_WINDOWS:
        return
    skip_reason = "Windows: 跳过数据库测试（greenlet DLL 不可用）"
    db_fixtures = {"async_client", "test_db", "test_user", "auth_headers", 
                   "test_project", "test_chapter"}
    for item in items:
        fixturenames = set(getattr(item, "fixturenames", []))
        if fixturenames & db_fixtures:
            item.add_marker(pytest.mark.skip(reason=skip_reason))


# ---------------------------------------------------------------------------
# Linux / macOS: 数据库和客户端固件
# ---------------------------------------------------------------------------

if not IS_WINDOWS:
    import pytest_asyncio
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
    from jose import jwt
    from datetime import datetime, timedelta, timezone

    import os
    TEST_DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite://")
    settings = get_settings()

    @pytest.fixture(scope="session")
    def event_loop():
        """会话级别事件循环。"""
        loop = asyncio.new_event_loop()
        yield loop
        loop.close()

    @pytest_asyncio.fixture(scope="session")
    async def test_engine():
        """创建测试数据库引擎。"""
        engine = create_async_engine(TEST_DATABASE_URL, echo=False)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        yield engine
        await engine.dispose()

    @pytest_asyncio.fixture()
    async def test_db(test_engine):
        """创建测试数据库会话。"""
        session_factory = async_sessionmaker(test_engine, expire_on_commit=False)
        async with session_factory() as session:
            yield session

    def _create_test_token(user_id: int) -> str:
        """为指定用户 ID 创建 JWT 测试令牌。"""
        now = datetime.now(timezone.utc)
        payload = {
            "sub": str(user_id),
            "type": "access",
            "exp": now + timedelta(minutes=15)
        }
        return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

    @pytest_asyncio.fixture()
    async def test_user(test_engine):
        """创建测试用户并返回 TokenResp（独立 session，不污染 test_db）。"""
        from app.service import auth_service
        from app.schemas.auth import RegisterReq, LoginReq
        
        email = "testuser@example.com"
        password = "TestPassword123!"
        
        session_factory = async_sessionmaker(test_engine, expire_on_commit=False)
        async with session_factory() as session:
            try:
                req = RegisterReq(email=email, nickname="测试用户", password=password)
                result = await auth_service.register(session, req)
                await session.commit()
                return result
            except Exception:
                await session.rollback()
                req = LoginReq(email=email, password=password)
                result = await auth_service.login(session, req)
                await session.commit()
                return result

    @pytest.fixture()
    def auth_headers(test_user):
        """返回带有 Bearer Token 的认证头。"""
        return {"Authorization": f"Bearer {test_user.access_token}"}

    @pytest_asyncio.fixture()
    async def async_client(test_db):
        """创建异步测试客户端。"""
        async def override_get_db():
            yield test_db
        
        app.dependency_overrides[get_db] = override_get_db
        
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            yield client
        
        app.dependency_overrides.clear()

    @pytest_asyncio.fixture()
    async def test_project(test_db, test_user):
        """创建测试项目。"""
        from app.service import project_service
        from app.schemas.project import CreateProjectReq
        
        req = CreateProjectReq(
            title="测试项目",
            author="测试作者",
            genre="玄幻",
            creation_mode="from_scratch"
        )
        
        project = await project_service.create_project(
            test_db, test_user.user.id, req
        )
        return project

    @pytest_asyncio.fixture()
    async def test_chapter(test_db, test_user, test_project):
        """创建测试章节。"""
        from app.service import chapter_service
        from app.schemas.chapter import CreateChapterReq
        
        req = CreateChapterReq(
            chapter_number=1,
            title="第一章 测试",
            content="测试内容。"
        )
        
        chapter = await chapter_service.create_chapter(
            test_db, test_user.user.id, test_project.id, req
        )
        return chapter
