"""墨灵 (Moling) — Pytest 配置。

提供测试固件：测试数据库、认证头、测试项目等。
支持 Windows / Linux / macOS 全平台。
"""

import sys
import platform
import os
import asyncio
import pytest
from typing import AsyncGenerator, Dict, Any

# ---------------------------------------------------------------------------
# 平台检测
# ---------------------------------------------------------------------------
IS_WINDOWS = platform.system() == "Windows"

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
# 全平台：event_loop fixture（异步测试必需）
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def event_loop():
    """会话级别事件循环 — 全平台提供。"""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()

# ---------------------------------------------------------------------------
# 非 Windows 平台：数据库固件
# ---------------------------------------------------------------------------

if not IS_WINDOWS:
    import pytest_asyncio
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
    from sqlalchemy.pool import NullPool
    from jose import jwt
    from datetime import datetime, timedelta, timezone

    TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL", "sqlite+aiosqlite://")
    settings = get_settings()
    _IS_PG = "postgresql" in TEST_DATABASE_URL

    @pytest_asyncio.fixture(scope="session")
    async def test_engine():
        """创建测试数据库引擎（PostgreSQL 用 NullPool 避免连接复用冲突）。"""
        engine_kwargs: dict = {"echo": False}
        if _IS_PG:
            engine_kwargs["poolclass"] = NullPool
        engine = create_async_engine(TEST_DATABASE_URL, **engine_kwargs)
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

    def _create_test_token(user_id) -> str:
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
    async def async_client(test_db, test_user):
        """创建异步测试客户端。"""
        async def override_get_db():
            yield test_db
        
        async def override_get_current_user():
            return test_user.user
        
        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user
        
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

# ---------------------------------------------------------------------------
# 收集阶段：Windows 跳过需要数据库固件的测试
# ---------------------------------------------------------------------------

def pytest_collection_modifyitems(config, items):
    """Windows 上跳过需要数据库固件的测试（greenlet 兼容性限制）。"""
    if not IS_WINDOWS:
        return
    skip_reason = "Windows: 跳过数据库测试（greenlet + pytest-asyncio 兼容性限制）"
    db_fixtures = {"async_client", "test_db", "test_user", "auth_headers", 
                   "test_project", "test_chapter", "test_engine"}
    for item in items:
        fixturenames = set(getattr(item, "fixturenames", []))
        if fixturenames & db_fixtures:
            item.add_marker(pytest.mark.skip(reason=skip_reason))
