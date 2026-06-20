"""墨灵 (Moling) — Secret API 端点测试。"""

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio

API_PREFIX = "/api/v1/secrets"


class TestSecretList:
    """测试秘密列表端点 GET /api/v1/secrets。"""

    async def test_list_secrets_success(self, async_client: AsyncClient, 
                                       auth_headers, test_project):
        """获取秘密列表成功应返回 200 及秘密数组。"""
        # Arrange
        params = {"project_id": test_project["id"]}

        # Act
        resp = await async_client.get(
            API_PREFIX, 
            headers=auth_headers,
            params=params
        )

        # Assert
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)

    async def test_list_secrets_no_project(self, async_client: AsyncClient, 
                                           auth_headers):
        """未提供项目 ID 应返回 422。"""
        # Act
        resp = await async_client.get(
            API_PREFIX, 
            headers=auth_headers
        )

        # Assert
        assert resp.status_code == 422

    async def test_list_secrets_no_auth(self, async_client: AsyncClient, 
                                        test_project):
        """未认证请求应返回 403。"""
        # Arrange
        params = {"project_id": test_project["id"]}

        # Act
        resp = await async_client.get(
            API_PREFIX, 
            params=params
        )

        # Assert
        assert resp.status_code == 401


class TestSecretGetByCharacter:
    """测试按角色获取秘密端点 GET /api/v1/secrets/character/{character_name}。"""

    async def test_get_secrets_by_character_success(self, async_client: AsyncClient, 
                                                    auth_headers, test_project):
        """获取角色秘密成功应返回 200 及字典。"""
        # Arrange
        params = {"project_id": test_project["id"]}
        character_name = "测试角色"

        # Act
        resp = await async_client.get(
            f"{API_PREFIX}/character/{character_name}", 
            headers=auth_headers,
            params=params
        )

        # Assert
        # 角色可能不存在，返回 200（空结果）或 404
        assert resp.status_code in [200, 404]
        if resp.status_code == 200:
            data = resp.json()
            assert isinstance(data, dict)

    async def test_get_secrets_by_character_not_found(self, async_client: AsyncClient, 
                                                       auth_headers, test_project):
        """获取不存在角色的秘密应返回 200 或 404。"""
        # Arrange
        params = {"project_id": test_project["id"]}
        character_name = "不存在的角色"

        # Act
        resp = await async_client.get(
            f"{API_PREFIX}/character/{character_name}", 
            headers=auth_headers,
            params=params
        )

        # Assert
        assert resp.status_code in [200, 404]


class TestSecretUpdate:
    """测试更新秘密端点 PATCH /api/v1/secrets/{secret_id}。"""

    async def test_update_secret_not_found(self, async_client: AsyncClient, 
                                          auth_headers, test_project):
        """更新不存在的秘密应返回 404。"""
        # Arrange
        params = {"project_id": test_project["id"]}
        payload = {"known_by": ["角色1"]}

        # Act
        resp = await async_client.patch(
            f"{API_PREFIX}/99999", 
            json=payload,
            headers=auth_headers,
            params=params
        )

        # Assert
        assert resp.status_code == 404

    async def test_update_secret_no_auth(self, async_client: AsyncClient, 
                                         test_project):
        """未认证请求应返回 403。"""
        # Arrange
        params = {"project_id": test_project["id"]}
        payload = {"known_by": ["角色1"]}

        # Act
        resp = await async_client.patch(
            f"{API_PREFIX}/1", 
            json=payload,
            params=params
        )

        # Assert
        assert resp.status_code == 401
