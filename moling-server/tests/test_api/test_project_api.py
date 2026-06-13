"""墨灵 (Moling) — Project API 端点测试。

覆盖创建、列表、统计、详情、删除。
"""

import pytest

pytestmark = pytest.mark.asyncio

API_PREFIX = "/api/v1/projects"


class TestProjectAPI:
    async def test_create_project(self, async_client, auth_headers):
        """创建项目应返回 201 及 ProjectResp。"""
        payload = {
            "title": "我的小说",
            "author": "墨灵作者",
            "genre": "玄幻",
            "creation_mode": "from_scratch",
        }
        resp = await async_client.post(
            API_PREFIX, json=payload, headers=auth_headers
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["title"] == "我的小说"
        assert data["author"] == "墨灵作者"
        assert data["genre"] == "玄幻"
        assert data["status"] == "draft"
        assert "id" in data

    async def test_list_projects(self, async_client, auth_headers, test_project):
        """列出项目应返回分页响应，包含刚创建的项目。"""
        resp = await async_client.get(API_PREFIX, headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1
        # items 可能是 dict 列表
        ids = [item["id"] for item in data["items"]]
        assert test_project.id in ids

    async def test_get_project_stats(self, async_client, auth_headers, test_project):
        """获取项目统计应返回总项目数/活跃/草稿等计数。"""
        resp = await async_client.get(
            f"{API_PREFIX}/stats", headers=auth_headers
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_projects"] >= 1
        assert data["draft_count"] >= 1

    async def test_get_project_detail(self, async_client, auth_headers, test_project):
        """获取单个项目详情应返回 ProjectResp。"""
        resp = await async_client.get(
            f"{API_PREFIX}/{test_project.id}", headers=auth_headers
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == test_project.id
        assert data["title"] == "测试项目"

    async def test_delete_project(self, async_client, auth_headers, test_project):
        """删除项目应返回 200 及成功消息。"""
        resp = await async_client.delete(
            f"{API_PREFIX}/{test_project.id}", headers=auth_headers
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["message"] == "项目已删除"

        # 验证删除后获取不到
        resp2 = await async_client.get(
            f"{API_PREFIX}/{test_project.id}", headers=auth_headers
        )
        assert resp2.status_code == 404
