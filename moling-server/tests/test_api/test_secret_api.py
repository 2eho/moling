"""墨灵 (Moling) — Secret API 端点测试。"""

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


class TestSecretList:
    """测试秘密列表端点 GET /api/v1/projects/{project_id}/secrets。"""

    async def test_list_secrets_success(self, async_client: AsyncClient, 
                                       auth_headers, test_project):
        """获取秘密列表成功应返回 200 及秘密数组。"""
        # Act
        resp = await async_client.get(
            f"/api/v1/projects/{test_project.id}/secrets", 
            headers=auth_headers
        )

        # Assert
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)

    async def test_list_secrets_no_project(self, async_client: AsyncClient, 
                                           auth_headers):
        """未提供项目 ID 应返回 404。"""
        # Act
        resp = await async_client.get(
            f"/api/v1/projects/99999/secrets", 
            headers=auth_headers
        )

        # Assert
        assert resp.status_code == 404

    async def test_list_secrets_no_auth(self, async_client: AsyncClient, 
                                        test_project):
        """未认证请求应返回 401。"""
        # Act
        resp = await async_client.get(
            f"/api/v1/projects/{test_project.id}/secrets"
        )

        # Assert
        assert resp.status_code == 401


class TestSecretGetByCharacter:
    """测试按角色获取秘密端点 GET /api/v1/projects/{project_id}/secrets/character/{character_name}。"""

    async def test_get_secrets_by_character_success(self, async_client: AsyncClient, 
                                                    auth_headers, test_project):
        """获取角色秘密成功应返回 200 及字典。"""
        # Arrange
        character_name = "测试角色"

        # Act
        resp = await async_client.get(
            f"/api/v1/projects/{test_project.id}/secrets/character/{character_name}", 
            headers=auth_headers
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
        character_name = "不存在的角色"

        # Act
        resp = await async_client.get(
            f"/api/v1/projects/{test_project.id}/secrets/character/{character_name}", 
            headers=auth_headers
        )

        # Assert
        assert resp.status_code in [200, 404]


class TestSecretUpdate:
    """测试更新秘密端点 PATCH /api/v1/projects/{project_id}/secrets/{secret_id}。"""

    async def test_update_secret_not_found(self, async_client: AsyncClient, 
                                          auth_headers, test_project):
        """更新不存在的秘密应返回 404。"""
        # Arrange
        payload = {"known_by": ["角色1"]}

        # Act
        resp = await async_client.patch(
            f"/api/v1/projects/{test_project.id}/secrets/99999", 
            json=payload,
            headers=auth_headers
        )

        # Assert
        assert resp.status_code == 404

    async def test_update_secret_no_auth(self, async_client: AsyncClient, 
                                         test_project):
        """未认证请求应返回 401。"""
        # Arrange
        payload = {"known_by": ["角色1"]}

        # Act
        resp = await async_client.patch(
            f"/api/v1/projects/{test_project.id}/secrets/1", 
            json=payload
        )

        # Assert
        assert resp.status_code == 401
