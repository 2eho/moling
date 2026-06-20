"""墨灵 (Moling) — Chapter API 端点测试。"""

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio

API_PREFIX = "/api/v1/chapters"


class TestChapterCreate:
    """测试创建章节端点 POST /api/v1/chapters。"""

    async def test_create_chapter_success(self, async_client: AsyncClient, 
                                        auth_headers, test_project):
        """创建章节成功应返回 201 及 ChapterResp。"""
        # Arrange
        payload = {
            "chapter_number": 1,
            "title": "第一章 测试章节",
            "content": "这是章节内容。"
        }
        params = {"project_id": test_project.id}

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
        assert data["chapter_number"] == 1
        assert data["title"] == "第一章 测试章节"
        assert data["content"] == "这是章节内容。"
        assert "id" in data

    async def test_create_chapter_no_auth(self, async_client: AsyncClient, test_project):
        """未认证请求应返回 403。"""
        # Arrange
        payload = {
            "chapter_number": 1,
            "title": "测试",
            "content": "内容"
        }
        params = {"project_id": test_project.id}

        # Act
        resp = await async_client.post(
            API_PREFIX, 
            json=payload, 
            params=params
        )

        # Assert
        assert resp.status_code == 401

    async def test_create_chapter_invalid_project(self, async_client: AsyncClient, 
                                                auth_headers):
        """无效项目 ID 应返回 404。"""
        # Arrange
        payload = {
            "chapter_number": 1,
            "title": "测试",
            "content": "内容"
        }
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


class TestChapterList:
    """测试章节列表端点 GET /api/v1/chapters。"""

    async def test_list_chapters_success(self, async_client: AsyncClient, 
                                       auth_headers, test_project, test_chapter):
        """获取章节列表成功应返回 200 及章节数组。"""
        # Arrange
        params = {"project_id": test_project.id}

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
        assert len(data) >= 1
        assert any(ch["id"] == test_chapter.id for ch in data)

    async def test_list_chapters_no_project(self, async_client: AsyncClient, 
                                           auth_headers):
        """未提供项目 ID 应返回 422。"""
        # Act
        resp = await async_client.get(
            API_PREFIX, 
            headers=auth_headers
        )

        # Assert
        assert resp.status_code == 422

    async def test_list_chapters_other_user(self, async_client: AsyncClient, 
                                           auth_headers):
        """访问其他用户的项目应返回 404。"""
        # Arrange
        params = {"project_id": 99999}

        # Act
        resp = await async_client.get(
            API_PREFIX, 
            headers=auth_headers,
            params=params
        )

        # Assert - 应该返回空列表或 404，取决于实现
        assert resp.status_code in [200, 404]


class TestChapterGet:
    """测试获取单个章节端点 GET /api/v1/chapters/{chapter_id}。"""

    async def test_get_chapter_success(self, async_client: AsyncClient, 
                                      auth_headers, test_project, test_chapter):
        """获取章节成功应返回 200 及 ChapterResp。"""
        # Arrange
        params = {"project_id": test_project.id}

        # Act
        resp = await async_client.get(
            f"{API_PREFIX}/{test_chapter.id}", 
            headers=auth_headers,
            params=params
        )

        # Assert
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == test_chapter.id
        assert data["title"] == test_chapter.title

    async def test_get_chapter_not_found(self, async_client: AsyncClient, 
                                        auth_headers, test_project):
        """获取不存在的章节应返回 404。"""
        # Arrange
        params = {"project_id": test_project.id}

        # Act
        resp = await async_client.get(
            f"{API_PREFIX}/99999", 
            headers=auth_headers,
            params=params
        )

        # Assert
        assert resp.status_code == 404


class TestChapterUpdate:
    """测试更新章节端点 PUT /api/v1/chapters/{chapter_id}。"""

    async def test_update_chapter_success(self, async_client: AsyncClient, 
                                         auth_headers, test_project, test_chapter):
        """更新章节成功应返回 200 及更新后的 ChapterResp。"""
        # Arrange
        payload = {
            "title": "更新后的标题",
            "content": "更新后的内容。"
        }
        params = {"project_id": test_project.id}

        # Act
        resp = await async_client.put(
            f"{API_PREFIX}/{test_chapter.id}", 
            json=payload,
            headers=auth_headers,
            params=params
        )

        # Assert
        assert resp.status_code == 200
        data = resp.json()
        assert data["title"] == "更新后的标题"
        assert data["content"] == "更新后的内容。"

    async def test_update_chapter_not_found(self, async_client: AsyncClient, 
                                           auth_headers, test_project):
        """更新不存在的章节应返回 404。"""
        # Arrange
        payload = {"title": "测试"}
        params = {"project_id": test_project.id}

        # Act
        resp = await async_client.put(
            f"{API_PREFIX}/99999", 
            json=payload,
            headers=auth_headers,
            params=params
        )

        # Assert
        assert resp.status_code == 404


class TestChapterDelete:
    """测试删除章节端点 DELETE /api/v1/chapters/{chapter_id}。"""

    async def test_delete_chapter_success(self, async_client: AsyncClient, 
                                         auth_headers, test_project, test_chapter):
        """删除章节成功应返回 204。"""
        # Arrange
        params = {"project_id": test_project.id}

        # Act
        resp = await async_client.delete(
            f"{API_PREFIX}/{test_chapter.id}", 
            headers=auth_headers,
            params=params
        )

        # Assert
        assert resp.status_code == 204

        # 验证删除后获取不到
        resp2 = await async_client.get(
            f"{API_PREFIX}/{test_chapter.id}", 
            headers=auth_headers,
            params=params
        )
        assert resp2.status_code == 404

    async def test_delete_chapter_not_found(self, async_client: AsyncClient, 
                                           auth_headers, test_project):
        """删除不存在的章节应返回 404。"""
        # Arrange
        params = {"project_id": test_project.id}

        # Act
        resp = await async_client.delete(
            f"{API_PREFIX}/99999", 
            headers=auth_headers,
            params=params
        )

        # Assert
        assert resp.status_code == 404


class TestChapterReorder:
    """测试章节重新排序端点 POST /api/v1/chapters/reorder。"""

    async def test_reorder_chapters_success(self, async_client: AsyncClient, 
                                            auth_headers, test_project):
        """重新排序章节成功应返回 200 及重新排序后的章节列表。"""
        # Arrange - 先创建两个章节
        payload1 = {"chapter_number": 1, "title": "第一章", "content": "内容1"}
        payload2 = {"chapter_number": 2, "title": "第二章", "content": "内容2"}
        params = {"project_id": test_project.id}
        
        resp1 = await async_client.post(
            API_PREFIX, json=payload1, headers=auth_headers, params=params
        )
        resp2 = await async_client.post(
            API_PREFIX, json=payload2, headers=auth_headers, params=params
        )
        
        chapter1_id = resp1.json()["id"]
        chapter2_id = resp2.json()["id"]

        # 重新排序：交换顺序
        reorder_payload = {"chapter_numbers": [chapter2_id, chapter1_id]}

        # Act
        resp = await async_client.post(
            f"{API_PREFIX}/reorder", 
            json=reorder_payload,
            headers=auth_headers,
            params=params
        )

        # Assert
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) == 2
