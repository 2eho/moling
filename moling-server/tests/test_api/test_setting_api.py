"""墨灵 (Moling) — Setting API 端点测试。"""

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio

API_PREFIX = "/api/v1/settings"


class TestSettingGet:
    """测试获取设置端点 GET /api/v1/settings。"""

    async def test_get_settings_success(self, async_client: AsyncClient, 
                                       auth_headers):
        """获取设置成功应返回 200 及 UserSettings。"""
        # Act
        resp = await async_client.get(
            API_PREFIX, 
            headers=auth_headers
        )

        # Assert
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, dict)

    async def test_get_settings_no_auth(self, async_client: AsyncClient):
        """未认证请求应返回 403。"""
        # Act
        resp = await async_client.get(API_PREFIX)

        # Assert
        assert resp.status_code == 403


class TestSettingUpdate:
    """测试更新设置端点 PUT /api/v1/settings。"""

    async def test_update_settings_success(self, async_client: AsyncClient, 
                                          auth_headers):
        """更新设置成功应返回 200 及更新后的 UserSettings。"""
        # Arrange
        payload = {
            "theme": "dark",
            "language": "zh-CN"
        }

        # Act
        resp = await async_client.put(
            API_PREFIX, 
            json=payload,
            headers=auth_headers
        )

        # Assert
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, dict)

    async def test_update_settings_no_auth(self, async_client: AsyncClient):
        """未认证请求应返回 403。"""
        # Arrange
        payload = {"theme": "light"}

        # Act
        resp = await async_client.put(
            API_PREFIX, 
            json=payload
        )

        # Assert
        assert resp.status_code == 403


class TestSettingChangePassword:
    """测试修改密码端点 POST /api/v1/settings/change-password。"""

    async def test_change_password_wrong_old(self, async_client: AsyncClient, 
                                             auth_headers):
        """错误旧密码应返回 400。"""
        # Arrange
        payload = {
            "old_password": "WrongPassword123!",
            "new_password": "NewPassword123!"
        }

        # Act
        resp = await async_client.post(
            f"{API_PREFIX}/change-password", 
            json=payload,
            headers=auth_headers
        )

        # Assert
        assert resp.status_code == 400

    async def test_change_password_no_auth(self, async_client: AsyncClient):
        """未认证请求应返回 403。"""
        # Arrange
        payload = {
            "old_password": "old",
            "new_password": "new"
        }

        # Act
        resp = await async_client.post(
            f"{API_PREFIX}/change-password", 
            json=payload
        )

        # Assert
        assert resp.status_code == 403


class TestSettingProfile:
    """测试个人资料端点。"""

    async def test_get_profile_success(self, async_client: AsyncClient, 
                                      auth_headers):
        """获取个人资料成功应返回 200 及资料字典。"""
        # Act
        resp = await async_client.get(
            f"{API_PREFIX}/profile", 
            headers=auth_headers
        )

        # Assert
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, dict)
        assert "email" in data or "username" in data

    async def test_update_profile_success(self, async_client: AsyncClient, 
                                         auth_headers):
        """更新个人资料成功应返回 200 及更新后的资料。"""
        # Arrange
        payload = {
            "username": "更新后的用户名",
            "bio": "这是个人简介。"
        }

        # Act
        resp = await async_client.put(
            f"{API_PREFIX}/profile", 
            json=payload,
            headers=auth_headers
        )

        # Assert
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, dict)
