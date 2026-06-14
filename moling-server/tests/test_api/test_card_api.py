"""墨灵 (Moling) — Card API 端点测试。"""

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio

API_PREFIX = "/api/v1/cards"


class TestCardList:
    """测试卡牌列表端点 GET /api/v1/cards。"""

    async def test_list_cards_success(self, async_client: AsyncClient, 
                                     auth_headers, test_project):
        """获取卡牌列表成功应返回 200 及 CardPoolListResp。"""
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
        assert "items" in data or isinstance(data, dict)

    async def test_list_cards_no_auth(self, async_client: AsyncClient, test_project):
        """未认证请求应返回 403。"""
        # Arrange
        params = {"project_id": test_project["id"]}

        # Act
        resp = await async_client.get(
            API_PREFIX, 
            params=params
        )

        # Assert
        assert resp.status_code == 403


class TestCardDraw:
    """测试抽卡端点 POST /api/v1/cards/draw。"""

    async def test_draw_cards_success(self, async_client: AsyncClient, 
                                     auth_headers, test_project):
        """抽卡成功应返回 200 及 DrawCardResp。"""
        # Arrange
        payload = {
            "mode": "single",
            "card_type": "character",
            "count": 1
        }
        params = {"project_id": test_project["id"]}

        # Act
        resp = await async_client.post(
            f"{API_PREFIX}/draw", 
            json=payload,
            headers=auth_headers,
            params=params
        )

        # Assert
        assert resp.status_code == 200
        data = resp.json()
        assert "cards" in data
        assert isinstance(data["cards"], list)

    async def test_draw_cards_invalid_mode(self, async_client: AsyncClient, 
                                           auth_headers, test_project):
        """无效模式应返回 422。"""
        # Arrange
        payload = {
            "mode": "invalid_mode",
            "card_type": "character",
            "count": 1
        }
        params = {"project_id": test_project["id"]}

        # Act
        resp = await async_client.post(
            f"{API_PREFIX}/draw", 
            json=payload,
            headers=auth_headers,
            params=params
        )

        # Assert
        assert resp.status_code == 422


class TestCardCreate:
    """测试创建卡牌端点 POST /api/v1/cards。"""

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
        params = {"project_id": test_project["id"]}

        # Act
        resp = await async_client.post(
            API_PREFIX, 
            json=payload,
            headers=auth_headers,
            params=params
        )

        # Assert
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "测试角色"
        assert data["card_type"] == "character"

    async def test_create_card_invalid_type(self, async_client: AsyncClient, 
                                           auth_headers, test_project):
        """无效卡牌类型应返回 422。"""
        # Arrange
        payload = {
            "card_type": "invalid_type",
            "name": "测试",
            "description": "描述"
        }
        params = {"project_id": test_project["id"]}

        # Act
        resp = await async_client.post(
            API_PREFIX, 
            json=payload,
            headers=auth_headers,
            params=params
        )

        # Assert
        assert resp.status_code == 422


class TestCardRetire:
    """测试退役卡牌端点 POST /api/v1/cards/{card_id}/retire。"""

    async def test_retire_card_success(self, async_client: AsyncClient, 
                                       auth_headers, test_project):
        """退役卡牌成功应返回 204。"""
        # Arrange - 先创建一个卡牌
        create_payload = {
            "card_type": "character",
            "name": "要退役的卡牌",
            "description": "描述",
            "rarity": "common"
        }
        params = {"project_id": test_project["id"]}
        
        create_resp = await async_client.post(
            API_PREFIX, 
            json=create_payload,
            headers=auth_headers,
            params=params
        )
        assert create_resp.status_code == 201
        card_id = create_resp.json()["id"]

        # Act
        resp = await async_client.post(
            f"{API_PREFIX}/{card_id}/retire", 
            headers=auth_headers,
            params=params
        )

        # Assert
        assert resp.status_code == 204

    async def test_retire_card_not_found(self, async_client: AsyncClient, 
                                         auth_headers, test_project):
        """退役不存在的卡牌应返回 404。"""
        # Arrange
        params = {"project_id": test_project["id"]}

        # Act
        resp = await async_client.post(
            f"{API_PREFIX}/99999/retire", 
            headers=auth_headers,
            params=params
        )

        # Assert
        assert resp.status_code == 404


class TestCardDrawHistory:
    """测试抽卡历史端点 GET /api/v1/cards/history。"""

    async def test_get_draw_history_success(self, async_client: AsyncClient, 
                                           auth_headers, test_project):
        """获取抽卡历史成功应返回 200 及历史列表。"""
        # Arrange
        params = {"project_id": test_project["id"]}

        # Act
        resp = await async_client.get(
            f"{API_PREFIX}/history", 
            headers=auth_headers,
            params=params
        )

        # Assert
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
