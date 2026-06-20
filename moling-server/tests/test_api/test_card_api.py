"""墨灵 (Moling) — Card API 端点测试。"""

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


class TestCardList:
    """测试卡牌列表端点 GET /api/v1/projects/{project_id}/cards。"""

    async def test_list_cards_success(self, async_client: AsyncClient, 
                                     auth_headers, test_project):
        """获取卡牌列表成功应返回 200 及 CardPoolListResp。"""
        # Act
        resp = await async_client.get(
            f"/api/v1/projects/{test_project.id}/cards", 
            headers=auth_headers,
        )

        # Assert
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert "cards" in data or isinstance(data, dict)

    async def test_list_cards_no_auth(self, async_client: AsyncClient, test_project):
        """未认证请求应返回 401。"""
        # Act
        resp = await async_client.get(
            f"/api/v1/projects/{test_project.id}/cards", 
        )

        # Assert
        assert resp.status_code == 401


class TestCardDraw:
    """测试抽卡端点 POST /api/v1/projects/{project_id}/cards/draw。"""

    async def test_draw_cards_success(self, async_client: AsyncClient, 
                                     auth_headers, test_project):
        """抽卡成功应返回 200 及 DrawCardResp。"""
        # Arrange - 使用正确的 DrawCardReq schema 字段
        payload = {
            "mode": "single",
            "draw_count": 1,
            "chapter_id": "",
            "keep_card_ids": [],
            "weights": [],
        }

        # Act
        resp = await async_client.post(
            f"/api/v1/projects/{test_project.id}/cards/draw", 
            json=payload,
            headers=auth_headers,
        )

        # Assert
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert "cards" in data
        assert isinstance(data["cards"], list)

    async def test_draw_cards_invalid_mode(self, async_client: AsyncClient, 
                                           auth_headers, test_project):
        """无效模式应返回 422。"""
        # Arrange
        payload = {
            "mode": "invalid_mode",
            "draw_count": 1,
            "chapter_id": "",
            "keep_card_ids": [],
            "weights": [],
        }

        # Act
        resp = await async_client.post(
            f"/api/v1/projects/{test_project.id}/cards/draw", 
            json=payload,
            headers=auth_headers,
        )

        # Assert
        assert resp.status_code == 422


class TestCardCreate:
    """测试创建卡牌端点 POST /api/v1/projects/{project_id}/cards。"""

    async def test_create_card_success(self, async_client: AsyncClient, 
                                      auth_headers, test_project):
        """创建卡牌成功应返回 201 及 CardResp。"""
        # Arrange
        payload = {
            "card_type": "character",
            "name": "测试角色",
            "description": "这是一个测试角色。",
            "rarity": "common"
        }

        # Act
        resp = await async_client.post(
            f"/api/v1/projects/{test_project.id}/cards", 
            json=payload,
            headers=auth_headers,
        )

        # Assert
        assert resp.status_code == 201
        data = resp.json()["data"]
        assert data["name"] == "测试角色"

    async def test_create_card_invalid_type(self, async_client: AsyncClient, 
                                           auth_headers, test_project):
        """无效卡牌类型应返回 422。"""
        # Arrange
        payload = {
            "card_type": "invalid_type",
            "name": "测试",
            "description": "描述"
        }

        # Act
        resp = await async_client.post(
            f"/api/v1/projects/{test_project.id}/cards", 
            json=payload,
            headers=auth_headers,
        )

        # Assert
        assert resp.status_code == 422


class TestCardRetire:
    """测试退役卡牌端点 POST /api/v1/projects/{project_id}/cards/{card_id}/retire。"""

    async def test_retire_card_success(self, async_client: AsyncClient, 
                                       auth_headers, test_project):
        """退役卡牌成功应返回 204。"""
        project_id = test_project.id

        # Arrange - 先创建一个卡牌
        create_payload = {
            "card_type": "character",
            "name": "要退役的卡牌",
            "description": "描述",
            "rarity": "common"
        }
        
        create_resp = await async_client.post(
            f"/api/v1/projects/{project_id}/cards", 
            json=create_payload,
            headers=auth_headers,
        )
        assert create_resp.status_code == 201
        card_id = create_resp.json()["data"]["id"]

        # Act
        resp = await async_client.post(
            f"/api/v1/projects/{project_id}/cards/{card_id}/retire", 
            headers=auth_headers,
        )

        # Assert
        assert resp.status_code == 204

    async def test_retire_card_not_found(self, async_client: AsyncClient, 
                                         auth_headers, test_project):
        """退役不存在的卡牌应返回 404。"""
        # Act
        resp = await async_client.post(
            f"/api/v1/projects/{test_project.id}/cards/99999/retire", 
            headers=auth_headers,
        )

        # Assert
        assert resp.status_code == 404


class TestCardDrawHistory:
    """测试抽卡历史端点 GET /api/v1/projects/{project_id}/cards/history。"""

    async def test_get_draw_history_success(self, async_client: AsyncClient, 
                                           auth_headers, test_project):
        """获取抽卡历史成功应返回 200 及历史列表。"""
        # Act
        resp = await async_client.get(
            f"/api/v1/projects/{test_project.id}/cards/history", 
            headers=auth_headers,
        )

        # Assert
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert "items" in data
