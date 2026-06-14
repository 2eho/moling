"""墨灵 (Moling) — 认证 API 端点测试。"""

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio

API_PREFIX = "/api/v1/auth"


class TestAuthRegister:
    """测试用户注册端点 POST /api/v1/auth/register。"""

    async def test_register_success(self, async_client: AsyncClient):
        """注册成功应返回 201 及 TokenResp。"""
        # Arrange
        payload = {
            "email": "newuser@example.com",
            "username": "新用户",
            "password": "Password123!"
        }

        # Act
        resp = await async_client.post(f"{API_PREFIX}/register", json=payload)

        # Assert
        assert resp.status_code == 201
        data = resp.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        assert "user" in data
        assert data["user"]["email"] == "newuser@example.com"
        assert data["user"]["username"] == "新用户"

    async def test_register_duplicate_email(self, async_client: AsyncClient, test_user):
        """重复注册相同邮箱应返回 400。"""
        # Arrange
        payload = {
            "email": test_user["user"]["email"],
            "username": "重复用户",
            "password": "Password123!"
        }

        # Act
        resp = await async_client.post(f"{API_PREFIX}/register", json=payload)

        # Assert
        assert resp.status_code == 400

    async def test_register_invalid_email(self, async_client: AsyncClient):
        """无效邮箱应返回 422（验证错误）。"""
        # Arrange
        payload = {
            "email": "invalid-email",
            "username": "测试",
            "password": "Password123!"
        }

        # Act
        resp = await async_client.post(f"{API_PREFIX}/register", json=payload)

        # Assert
        assert resp.status_code == 422

    async def test_register_short_password(self, async_client: AsyncClient):
        """密码太短应返回 422（验证错误）。"""
        # Arrange
        payload = {
            "email": "short@example.com",
            "username": "测试",
            "password": "123"
        }

        # Act
        resp = await async_client.post(f"{API_PREFIX}/register", json=payload)

        # Assert
        assert resp.status_code == 422


class TestAuthLogin:
    """测试用户登录端点 POST /api/v1/auth/login。"""

    async def test_login_success(self, async_client: AsyncClient, test_user):
        """登录成功应返回 200 及 TokenResp。"""
        # Arrange
        payload = {
            "email": test_user["user"]["email"],
            "password": "TestPassword123!"
        }

        # Act
        resp = await async_client.post(f"{API_PREFIX}/login", json=payload)

        # Assert
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        assert data["user"]["email"] == test_user["user"]["email"]

    async def test_login_wrong_password(self, async_client: AsyncClient, test_user):
        """错误密码应返回 401。"""
        # Arrange
        payload = {
            "email": test_user["user"]["email"],
            "password": "WrongPassword123!"
        }

        # Act
        resp = await async_client.post(f"{API_PREFIX}/login", json=payload)

        # Assert
        assert resp.status_code == 401

    async def test_login_nonexistent_email(self, async_client: AsyncClient):
        """不存在的邮箱应返回 401。"""
        # Arrange
        payload = {
            "email": "nonexistent@example.com",
            "password": "Password123!"
        }

        # Act
        resp = await async_client.post(f"{API_PREFIX}/login", json=payload)

        # Assert
        assert resp.status_code == 401

    async def test_login_invalid_credentials(self, async_client: AsyncClient):
        """无效凭据应返回 422。"""
        # Arrange
        payload = {
            "email": "not-an-email",
            "password": ""
        }

        # Act
        resp = await async_client.post(f"{API_PREFIX}/login", json=payload)

        # Assert
        assert resp.status_code == 422


class TestAuthRefresh:
    """测试刷新令牌端点 POST /api/v1/auth/refresh。"""

    async def test_refresh_success(self, async_client: AsyncClient, test_user):
        """使用有效刷新令牌应返回新 TokenResp。"""
        # Arrange
        payload = {"refresh_token": test_user["refresh_token"]}

        # Act
        resp = await async_client.post(f"{API_PREFIX}/refresh", json=payload)

        # Assert
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert "refresh_token" in data
        # 新 access_token 应该不同
        assert data["access_token"] != test_user["access_token"]

    async def test_refresh_invalid_token(self, async_client: AsyncClient):
        """无效刷新令牌应返回 401。"""
        # Arrange
        payload = {"refresh_token": "invalid.token.here"}

        # Act
        resp = await async_client.post(f"{API_PREFIX}/refresh", json=payload)

        # Assert
        assert resp.status_code == 401

    async def test_refresh_empty_token(self, async_client: AsyncClient):
        """空刷新令牌应返回 422。"""
        # Arrange
        payload = {"refresh_token": ""}

        # Act
        resp = await async_client.post(f"{API_PREFIX}/refresh", json=payload)

        # Assert
        assert resp.status_code == 422


class TestAuthGetMe:
    """测试获取当前用户信息端点 GET /api/v1/auth/me。"""

    async def test_get_me_success(self, async_client: AsyncClient, auth_headers, test_user):
        """使用有效令牌应返回用户信息。"""
        # Act
        resp = await async_client.get(f"{API_PREFIX}/me", headers=auth_headers)

        # Assert
        assert resp.status_code == 200
        data = resp.json()
        assert data["email"] == test_user["user"]["email"]
        assert data["username"] == test_user["user"]["username"]
        assert "id" in data

    async def test_get_me_no_token(self, async_client: AsyncClient):
        """无令牌请求应返回 403（未认证）。"""
        # Act
        resp = await async_client.get(f"{API_PREFIX}/me")

        # Assert
        assert resp.status_code == 403

    async def test_get_me_invalid_token(self, async_client: AsyncClient):
        """无效令牌应返回 401。"""
        # Arrange
        headers = {"Authorization": "Bearer invalid.token"}

        # Act
        resp = await async_client.get(f"{API_PREFIX}/me", headers=headers)

        # Assert
        assert resp.status_code == 401
