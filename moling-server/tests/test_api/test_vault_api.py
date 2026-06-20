"""墨灵 (Moling) — Vault API 端点测试（四库：人物、时间线、剧情承诺、世界观）。"""

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


class TestVaultCharacter:
    """测试人物库端点。"""

    async def test_list_characters_success(self, async_client: AsyncClient, 
                                          auth_headers, test_project):
        """获取人物列表成功应返回 200 及人物数组（APIResponse 包裹）。"""
        # Arrange

        # Act
        resp = await async_client.get(
            f"/api/v1/projects/{test_project.id}/vault/characters", 
            headers=auth_headers
        )

        # Assert
        assert resp.status_code == 200
        payload = resp.json()
        assert "data" in payload
        assert isinstance(payload["data"]["items"], list)

    async def test_create_character_success(self, async_client: AsyncClient, 
                                            auth_headers, test_project):
        """创建人物成功应返回 201 及 CharacterResp。"""
        # Arrange
        payload = {
            "name": "测试角色",
            "role": "主角",
            "description": "这是一个测试角色。",
            "traits": ["勇敢", "正直"],
            "relationships": {}
        }

        # Act
        resp = await async_client.post(
            f"/api/v1/projects/{test_project.id}/vault/characters", 
            json=payload,
            headers=auth_headers
        )

        # Assert
        assert resp.status_code == 201
        data = resp.json()
        assert data["data"]["name"] == "测试角色"

    async def test_update_character_success(self, async_client: AsyncClient, 
                                            auth_headers, test_project):
        """更新人物成功应返回 200 及更新后的 CharacterResp。"""
        # Arrange - 先创建一个人物
        create_payload = {
            "name": "要更新的角色",
            "role": "配角",
            "description": "描述"
        }
        
        create_resp = await async_client.post(
            f"/api/v1/projects/{test_project.id}/vault/characters", 
            json=create_payload,
            headers=auth_headers
        )
        assert create_resp.status_code == 201
        character_id = create_resp.json()["data"]["id"]

        # 更新
        update_payload = {
            "name": "更新后的角色",
            "role": "配角",
            "description": "更新后的描述"
        }

        # Act
        resp = await async_client.put(
            f"/api/v1/projects/{test_project.id}/vault/characters/{character_id}", 
            json=update_payload,
            headers=auth_headers
        )

        # Assert
        assert resp.status_code == 200
        data = resp.json()
        assert data["data"]["name"] == "更新后的角色"

    async def test_delete_character_success(self, async_client: AsyncClient, 
                                            auth_headers, test_project):
        """删除人物成功应返回 204。"""
        # Arrange - 先创建一个人物
        create_payload = {
            "name": "要删除的角色",
            "role": "龙套",
            "description": "描述"
        }
        
        create_resp = await async_client.post(
            f"/api/v1/projects/{test_project.id}/vault/characters", 
            json=create_payload,
            headers=auth_headers
        )
        assert create_resp.status_code == 201
        character_id = create_resp.json()["data"]["id"]

        # Act
        resp = await async_client.delete(
            f"/api/v1/projects/{test_project.id}/vault/characters/{character_id}", 
            headers=auth_headers
        )

        # Assert
        assert resp.status_code == 204


class TestVaultTimeline:
    """测试时间线端点。"""

    async def test_list_timeline_success(self, async_client: AsyncClient, 
                                        auth_headers, test_project):
        """获取时间线事件列表成功应返回 200 及事件数组（APIResponse 包裹）。"""
        # Arrange

        # Act
        resp = await async_client.get(
            f"/api/v1/projects/{test_project.id}/vault/timeline", 
            headers=auth_headers
        )

        # Assert
        assert resp.status_code == 200
        payload = resp.json()
        assert "data" in payload
        assert isinstance(payload["data"]["items"], list)

    async def test_create_timeline_event_success(self, async_client: AsyncClient, 
                                                 auth_headers, test_project):
        """创建时间线事件成功应返回 201 及 TimelineResp。"""
        # Arrange
        payload = {
            "chapter_number": 1,
            "event": "测试事件",
            "description": "这是一个测试事件。",
        }

        # Act
        resp = await async_client.post(
            f"/api/v1/projects/{test_project.id}/vault/timeline", 
            json=payload,
            headers=auth_headers
        )

        # Assert
        assert resp.status_code == 201
        data = resp.json()
        assert data["data"]["event"] == "测试事件"


class TestVaultPlotPromise:
    """测试剧情承诺端点。"""

    async def test_list_plot_promises_success(self, async_client: AsyncClient, 
                                              auth_headers, test_project):
        """获取剧情承诺列表成功应返回 200 及承诺数组（APIResponse 包裹）。"""
        # Arrange

        # Act
        resp = await async_client.get(
            f"/api/v1/projects/{test_project.id}/vault/plot-promises", 
            headers=auth_headers
        )

        # Assert
        assert resp.status_code == 200
        payload = resp.json()
        assert "data" in payload
        assert isinstance(payload["data"]["items"], list)

    async def test_create_plot_promise_success(self, async_client: AsyncClient, 
                                               auth_headers, test_project):
        """创建剧情承诺成功应返回 201 及 PlotPromiseResp。"""
        # Arrange
        payload = {
            "description": "测试承诺",
            "type": "伏笔",
        }

        # Act
        resp = await async_client.post(
            f"/api/v1/projects/{test_project.id}/vault/plot-promises", 
            json=payload,
            headers=auth_headers
        )

        # Assert
        assert resp.status_code == 201
        data = resp.json()
        assert data["data"]["description"] == "测试承诺"


class TestVaultWorld:
    """测试世界观端点。"""

    async def test_list_world_entries_success(self, async_client: AsyncClient, 
                                             auth_headers, test_project):
        """获取世界观条目列表成功应返回 200 及条目数组（APIResponse 包裹）。"""
        # Arrange

        # Act
        resp = await async_client.get(
            f"/api/v1/projects/{test_project.id}/vault/world", 
            headers=auth_headers
        )

        # Assert
        assert resp.status_code == 200
        payload = resp.json()
        assert "data" in payload
        assert isinstance(payload["data"]["items"], list)

    async def test_create_world_entry_success(self, async_client: AsyncClient, 
                                              auth_headers, test_project):
        """创建世界观条目成功应返回 201 及 WorldResp。"""
        # Arrange
        payload = {
            "name": "测试世界观",
            "description": "这是一个测试世界观条目。",
            "category": "魔法体系"
        }

        # Act
        resp = await async_client.post(
            f"/api/v1/projects/{test_project.id}/vault/world", 
            json=payload,
            headers=auth_headers
        )

        # Assert
        assert resp.status_code == 201
        data = resp.json()
        assert data["data"]["name"] == "测试世界观"
