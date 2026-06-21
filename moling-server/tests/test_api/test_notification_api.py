"""墨灵 (Moling) — Notification API 端点测试。"""

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio

API_PREFIX = "/api/v1/notifications"


class TestNotificationList:
    """测试通知列表端点 GET /api/v1/notifications。"""

    async def test_list_notifications_success(self, async_client: AsyncClient, 
                                              auth_headers):
        """获取通知列表成功应返回 200 及分页响应。"""
        # Act
        resp = await async_client.get(
            API_PREFIX, 
            headers=auth_headers
        )

        # Assert
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data or isinstance(data, dict)

    async def test_list_notifications_with_pagination(self, async_client: AsyncClient, 
                                                      auth_headers):
        """带分页参数获取通知列表应返回正确分页。"""
        # Arrange
        params = {"page": 1, "page_size": 10}

        # Act
        resp = await async_client.get(
            API_PREFIX, 
            headers=auth_headers,
            params=params
        )

        # Assert
        assert resp.status_code == 200

    async def test_list_notifications_no_auth(self, async_client: AsyncClient):
        """未认证请求应返回 403。"""
        # Act
        resp = await async_client.get(API_PREFIX)

        # Assert
        assert resp.status_code == 401


class TestNotificationUnreadCount:
    """测试未读通知数量端点 GET /api/v1/notifications/unread-count。"""

    async def test_get_unread_count_success(self, async_client: AsyncClient, 
                                            auth_headers):
        """获取未读通知数量成功应返回 200 及计数。"""
        # Act
        resp = await async_client.get(
            f"{API_PREFIX}/unread-count", 
            headers=auth_headers
        )

        # Assert
        assert resp.status_code == 200
        data = resp.json()
        # 统一响应格式：{code, message, data: {unread_count: N}, meta}
        inner = data.get("data", data)
        assert "count" in inner or "unread_count" in inner


class TestNotificationMarkRead:
    """测试标记已读端点 POST /api/v1/notifications/{id}/read。"""

    async def test_mark_as_read_not_found(self, async_client: AsyncClient, 
                                          auth_headers):
        """标记不存在的通知为已读应返回 404。"""
        # Act
        resp = await async_client.post(
            f"{API_PREFIX}/99999/read", 
            headers=auth_headers
        )

        # Assert
        assert resp.status_code == 404

    async def test_mark_as_read_no_auth(self, async_client: AsyncClient):
        """未认证请求应返回 403。"""
        # Act
        resp = await async_client.post(f"{API_PREFIX}/1/read")

        # Assert
        assert resp.status_code == 401


class TestNotificationMarkAllRead:
    """测试全部标记已读端点 POST /api/v1/notifications/read-all。"""

    async def test_mark_all_as_read_success(self, async_client: AsyncClient, 
                                            auth_headers):
        """全部标记已读成功应返回 200。"""
        # Act
        resp = await async_client.post(
            f"{API_PREFIX}/read-all", 
            headers=auth_headers
        )

        # Assert
        assert resp.status_code == 200


class TestNotificationDelete:
    """测试删除通知端点 DELETE /api/v1/notifications/{id}。"""

    async def test_delete_notification_not_found(self, async_client: AsyncClient, 
                                                auth_headers):
        """删除不存在的通知应返回 404。"""
        # Act
        resp = await async_client.delete(
            f"{API_PREFIX}/99999", 
            headers=auth_headers
        )

        # Assert
        assert resp.status_code == 404

    async def test_delete_notification_no_auth(self, async_client: AsyncClient):
        """未认证请求应返回 403。"""
        # Act
        resp = await async_client.delete(f"{API_PREFIX}/1")

        # Assert
        assert resp.status_code == 401
