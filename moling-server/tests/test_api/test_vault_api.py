"""墨灵 (Moling) — Vault API 端点测试（四库：人物、时间线、剧情承诺、世界观）。"""

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio

API_PREFIX = "/api/v1/vault"


class TestVaultCharacter:
    """测试人物库端点。"""

    async def test_list_characters_success(self, async_client: AsyncClient, 
                                          auth_headers, test_project):
        """获取人物列表成功应返回 200 及人物数组。"""
        # Arrange
        params = {"project_id": test_project["id"]}

        # Act
        resp = await async_client.get(
            f"{API_PREFIX}/characters", 
            headers=auth_headers,
            params=params
        )

        # Assert
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)

    async def test_create_character_success(self, async_client: AsyncClient, 
                                            auth_headers, test_project):
        """创建人物成功应返回 201 及 CharacterResp。"""
        # Arrange
        payload = {
            "name": "测试角色",
            "description": "这是一个测试角色。",
            "traits": ["勇敢", "正直"],
            "relationships": {}
        }
        params = {"project_id": test_project["id"]}

        # Act
        resp = await async_client.post(
            f"{API_PREFIX}/characters", 
            json=payload,
            headers=auth_headers,
            params=params
        )

        # Assert
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "测试角色"

    async def test_update_character_success(self, async_client: AsyncClient, 
                                            auth_headers, test_project):
        """更新人物成功应返回 200 及更新后的 CharacterResp。"""
        # Arrange - 先创建一个人物
        create_payload = {
            "name": "要更新的角色",
            "description": "描述"
        }
        params = {"project_id": test_project["id"]}
        
        create_resp = await async_client.post(
            f"{API_PREFIX}/characters", 
            json=create_payload,
            headers=auth_headers,
            params=params
        )
        assert create_resp.status_code == 201
        character_id = create_resp.json()["id"]

        # 更新
        update_payload = {
            "name": "更新后的角色",
            "description": "更新后的描述"
        }

        # Act
        resp = await async_client.put(
            f"{API_PREFIX}/characters/{character_id}", 
            json=update_payload,
            headers=auth_headers,
            params=params
        )

        # Assert
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "更新后的角色"

    async def test_delete_character_success(self, async_client: AsyncClient, 
                                            auth_headers, test_project):
        """删除人物成功应返回 204。"""
        # Arrange - 先创建一个人物
        create_payload = {
            "name": "要删除的角色",
            "description": "描述"
        }
        params = {"project_id": test_project["id"]}
        
        create_resp = await async_client.post(
            f"{API_PREFIX}/characters", 
            json=create_payload,
            headers=auth_headers,
            params=params
        )
        assert create_resp.status_code == 201
        character_id = create_resp.json()["id"]

        # Act
        resp = await async_client.delete(
            f"{API_PREFIX}/characters/{character_id}", 
            headers=auth_headers,
            params=params
        )

        # Assert
        assert resp.status_code == 204


class TestVaultTimeline:
    """测试时间线端点。"""

    async def test_list_timeline_success(self, async_client: AsyncClient, 
                                        auth_headers, test_project):
        """获取时间线事件列表成功应返回 200 及事件数组。"""
        # Arrange
        params = {"project_id": test_project["id"]}

        # Act
        resp = await async_client.get(
            f"{API_PREFIX}/timeline", 
            headers=auth_headers,
            params=params
        )

        # Assert
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)

    async def test_create_timeline_event_success(self, async_client: AsyncClient, 
                                                 auth_headers, test_project):
        """创建时间线事件成功应返回 201 及 TimelineResp。"""
        # Arrange
        payload = {
            "event_name": "测试事件",
            "description": "这是一个测试事件。",
            "order": 1
        }
        params = {"project_id": test_project["id"]}

        # Act
        resp = await async_client.post(
            f"{API_PREFIX}/timeline", 
            json=payload,
            headers=auth_headers,
            params=params
        )

        # Assert
        assert resp.status_code == 201
        data = resp.json()
        assert data["event_name"] == "测试事件"


class TestVaultPlotPromise:
    """测试剧情承诺端点。"""

    async def test_list_plot_promises_success(self, async_client: AsyncClient, 
                                              auth_headers, test_project):
        """获取剧情承诺列表成功应返回 200 及承诺数组。"""
        # Arrange
        params = {"project_id": test_project["id"]}

        # Act
        resp = await async_client.get(
            f"{API_PREFIX}/plot-promises", 
            headers=auth_headers,
            params=params
        )

        # Assert
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)

    async def test_create_plot_promise_success(self, async_client: AsyncClient, 
                                               auth_headers, test_project):
        """创建剧情承诺成功应返回 201 及 PlotPromiseResp。"""
        # Arrange
        payload = {
            "promise_text": "测试承诺",
            "status": "pending"
        }
        params = {"project_id": test_project["id"]}

        # Act
        resp = await async_client.post(
            f"{API_PREFIX}/plot-promises", 
            json=payload,
            headers=auth_headers,
            params=params
        )

        # Assert
        assert resp.status_code == 201
        data = resp.json()
        assert data["promise_text"] == "测试承诺"


class TestVaultWorld:
    """测试世界观端点。"""

    async def test_list_world_entries_success(self, async_client: AsyncClient, 
                                             auth_headers, test_project):
        """获取世界观条目列表成功应返回 200 及条目数组。"""
        # Arrange
        params = {"project_id": test_project["id"]}

        # Act
        resp = await async_client.get(
            f"{API_PREFIX}/world", 
            headers=auth_headers,
            params=params
        )

        # Assert
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)

    async def test_create_world_entry_success(self, async_client: AsyncClient, 
                                              auth_headers, test_project):
        """创建世界观条目成功应返回 201 及 WorldResp。"""
        # Arrange
        payload = {
            "entry_name": "测试世界观",
            "description": "这是一个测试世界观条目。",
            "category": "魔法体系"
        }
        params = {"project_id": test_project["id"]}

        # Act
        resp = await async_client.post(
            f"{API_PREFIX}/world", 
            json=payload,
            headers=auth_headers,
            params=params
        )

        # Assert
        assert resp.status_code == 201
        data = resp.json()
        assert data["entry_name"] == "测试世界观"
