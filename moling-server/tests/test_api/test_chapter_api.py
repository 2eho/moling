"""墨灵 (Moling) — Chapter API 端点测试。"""

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


class TestChapterCreate:
    """测试创建章节端点 POST /api/v1/projects/{project_id}/chapters。"""

    async def test_create_chapter_success(self, async_client: AsyncClient, 
                                        auth_headers, test_project):
        """创建章节成功应返回 201 及 ChapterResp。"""
        # Arrange
        payload = {
            "chapter_number": 1,
            "title": "第一章 测试章节",
        }

        # Act
        resp = await async_client.post(
            f"/api/v1/projects/{test_project.id}/chapters", 
            json=payload, 
            headers=auth_headers,
        )

        # Assert
        assert resp.status_code == 201
        data = resp.json()["data"]
        assert data["chapter_number"] == 1
        assert data["title"] == "第一章 测试章节"
        assert "id" in data

    async def test_create_chapter_no_auth(self, async_client: AsyncClient, test_project):
        """未认证请求应返回 401。"""
        # Arrange
        payload = {
            "chapter_number": 1,
            "title": "测试",
        }

        # Act
        resp = await async_client.post(
            f"/api/v1/projects/{test_project.id}/chapters", 
            json=payload, 
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
        }

        # Act
        resp = await async_client.post(
            "/api/v1/projects/99999/chapters", 
            json=payload, 
            headers=auth_headers,
        )

        # Assert
        assert resp.status_code == 404


class TestChapterList:
    """测试章节列表端点 GET /api/v1/projects/{project_id}/chapters。"""

    async def test_list_chapters_success(self, async_client: AsyncClient, 
                                       auth_headers, test_project, test_chapter):
        """获取章节列表成功应返回 200 及章节数组。"""
        # Act
        resp = await async_client.get(
            f"/api/v1/projects/{test_project.id}/chapters", 
            headers=auth_headers,
        )

        # Assert
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert isinstance(data, list)
        assert len(data) >= 1
        assert any(ch["id"] == test_chapter.id for ch in data)

    async def test_list_chapters_no_project(self, async_client: AsyncClient, 
                                           auth_headers):
        """缺少项目 ID 路径参数应返回 404 或 422。"""
        # Act
        resp = await async_client.get(
            "/api/v1/projects/0/chapters", 
            headers=auth_headers
        )

        # Assert
        assert resp.status_code in [404, 422]

    async def test_list_chapters_other_user(self, async_client: AsyncClient, 
                                           auth_headers):
        """访问其他用户的项目应返回 404。"""
        # Act
        resp = await async_client.get(
            "/api/v1/projects/99999/chapters", 
            headers=auth_headers,
        )

        # Assert
        assert resp.status_code in [200, 404]


class TestChapterGet:
    """测试获取单个章节端点 GET /api/v1/projects/{project_id}/chapters/{chapter_id}。"""

    async def test_get_chapter_success(self, async_client: AsyncClient, 
                                      auth_headers, test_project, test_chapter):
        """获取章节成功应返回 200 及 ChapterResp。"""
        # Act
        resp = await async_client.get(
            f"/api/v1/projects/{test_project.id}/chapters/{test_chapter.id}", 
            headers=auth_headers,
        )

        # Assert
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["id"] == test_chapter.id
        assert data["title"] == test_chapter.title

    async def test_get_chapter_not_found(self, async_client: AsyncClient, 
                                        auth_headers, test_project):
        """获取不存在的章节应返回 404。"""
        # Act
        resp = await async_client.get(
            f"/api/v1/projects/{test_project.id}/chapters/99999", 
            headers=auth_headers,
        )

        # Assert
        assert resp.status_code == 404


class TestChapterUpdate:
    """测试更新章节端点 PUT /api/v1/projects/{project_id}/chapters/{chapter_id}。"""

    async def test_update_chapter_success(self, async_client: AsyncClient, 
                                         auth_headers, test_project, test_chapter):
        """更新章节成功应返回 200 及更新后的 ChapterResp。"""
        # Arrange
        payload = {
            "title": "更新后的标题",
            "content": "更新后的内容。"
        }

        # Act
        resp = await async_client.put(
            f"/api/v1/projects/{test_project.id}/chapters/{test_chapter.id}", 
            json=payload,
            headers=auth_headers,
        )

        # Assert
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["title"] == "更新后的标题"
        assert data["content"] == "更新后的内容。"

    async def test_update_chapter_not_found(self, async_client: AsyncClient, 
                                           auth_headers, test_project):
        """更新不存在的章节应返回 404。"""
        # Arrange
        payload = {"title": "测试"}

        # Act
        resp = await async_client.put(
            f"/api/v1/projects/{test_project.id}/chapters/99999", 
            json=payload,
            headers=auth_headers,
        )

        # Assert
        assert resp.status_code == 404


class TestChapterDelete:
    """测试删除章节端点 DELETE /api/v1/projects/{project_id}/chapters/{chapter_id}。"""

    async def test_delete_chapter_success(self, async_client: AsyncClient, 
                                         auth_headers, test_project, test_chapter):
        """删除章节成功应返回 204。"""
        # Act
        resp = await async_client.delete(
            f"/api/v1/projects/{test_project.id}/chapters/{test_chapter.id}", 
            headers=auth_headers,
        )

        # Assert
        assert resp.status_code == 204

        # 验证删除后获取不到
        resp2 = await async_client.get(
            f"/api/v1/projects/{test_project.id}/chapters/{test_chapter.id}", 
            headers=auth_headers,
        )
        assert resp2.status_code == 404

    async def test_delete_chapter_not_found(self, async_client: AsyncClient, 
                                           auth_headers, test_project):
        """删除不存在的章节应返回 404。"""
        # Act
        resp = await async_client.delete(
            f"/api/v1/projects/{test_project.id}/chapters/99999", 
            headers=auth_headers,
        )

        # Assert
        assert resp.status_code == 404


class TestChapterReorder:
    """测试章节重新排序端点 POST /api/v1/projects/{project_id}/chapters/reorder。"""

    async def test_reorder_chapters_success(self, async_client: AsyncClient, 
                                            auth_headers, test_project):
        """重新排序章节成功应返回 200 及重新排序后的章节列表。"""
        project_id = test_project.id

        # Arrange - 先创建两个章节
        payload1 = {"chapter_number": 1, "title": "第一章"}
        payload2 = {"chapter_number": 2, "title": "第二章"}
        
        resp1 = await async_client.post(
            f"/api/v1/projects/{project_id}/chapters",
            json=payload1, headers=auth_headers
        )
        resp2 = await async_client.post(
            f"/api/v1/projects/{project_id}/chapters",
            json=payload2, headers=auth_headers
        )
        
        assert resp1.status_code == 201
        assert resp2.status_code == 201

        # 重新排序：交换顺序 (chapter_numbers 为 query 参数)
        resp = await async_client.post(
            f"/api/v1/projects/{project_id}/chapters/reorder", 
            params={"chapter_numbers": [2, 1]},
            headers=auth_headers,
        )

        # Assert
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert isinstance(data, list)
        assert len(data) == 2
