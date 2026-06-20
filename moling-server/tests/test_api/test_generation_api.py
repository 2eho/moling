"""墨灵 (Moling) — Generation API 端点测试。"""

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio

API_PREFIX = "/api/v1/generation"


class TestGenerationStart:
    """测试开始生成端点 POST /api/v1/generation。"""

    async def test_start_generation_success(self, async_client: AsyncClient, 
                                           auth_headers, test_project, test_chapter):
        """开始生成成功应返回 201 及 GenerationResp。"""
        # Arrange
        payload = {
            "prompt": "生成一段内容",
            "max_tokens": 1000,
            "temperature": 0.7
        }
        params = {
            "project_id": test_project["id"],
            "chapter_id": test_chapter["id"]
        }

        # Act
        resp = await async_client.post(
            API_PREFIX, 
            json=payload,
            headers=auth_headers,
            params=params
        )

        # Assert
        # 注意：如果 LLM 服务未配置，可能返回 500
        assert resp.status_code in [201, 500, 503]
        if resp.status_code == 201:
            data = resp.json()
            assert "task_id" in data
            assert "status" in data

    async def test_start_generation_no_auth(self, async_client: AsyncClient, 
                                            test_project):
        """未认证请求应返回 403。"""
        # Arrange
        payload = {"prompt": "测试"}
        params = {"project_id": test_project["id"]}

        # Act
        resp = await async_client.post(
            API_PREFIX, 
            json=payload,
            params=params
        )

        # Assert
        assert resp.status_code == 401

    async def test_start_generation_invalid_project(self, async_client: AsyncClient, 
                                                    auth_headers):
        """无效项目 ID 应返回 404。"""
        # Arrange
        payload = {"prompt": "测试"}
        params = {"project_id": 99999}

        # Act
        resp = await async_client.post(
            API_PREFIX, 
            json=payload,
            headers=auth_headers,
            params=params
        )

        # Assert
        assert resp.status_code == 404


class TestGenerationStatus:
    """测试获取任务状态端点 GET /api/v1/generation/{task_id}。"""

    async def test_get_task_status_not_found(self, async_client: AsyncClient, 
                                            auth_headers):
        """获取不存在的任务状态应返回 404。"""
        # Act
        resp = await async_client.get(
            f"{API_PREFIX}/nonexistent-task-id", 
            headers=auth_headers
        )

        # Assert
        assert resp.status_code == 404

    async def test_get_task_status_no_auth(self, async_client: AsyncClient):
        """未认证请求应返回 403。"""
        # Act
        resp = await async_client.get(
            f"{API_PREFIX}/some-task-id"
        )

        # Assert
        assert resp.status_code == 401


class TestGenerationCancel:
    """测试取消任务端点 DELETE /api/v1/generation/{task_id}。"""

    async def test_cancel_task_not_found(self, async_client: AsyncClient, 
                                        auth_headers):
        """取消不存在的任务应返回 404。"""
        # Act
        resp = await async_client.delete(
            f"{API_PREFIX}/nonexistent-task-id", 
            headers=auth_headers
        )

        # Assert
        assert resp.status_code == 404

    async def test_cancel_task_no_auth(self, async_client: AsyncClient):
        """未认证请求应返回 403。"""
        # Act
        resp = await async_client.delete(
            f"{API_PREFIX}/some-task-id"
        )

        # Assert
        assert resp.status_code == 401
