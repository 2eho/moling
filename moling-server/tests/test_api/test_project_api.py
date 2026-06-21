"""墨灵 (Moling) — Project API 端点测试。

覆盖创建、列表、统计、详情、删除。
"""

import pytest

pytestmark = pytest.mark.asyncio

API_PREFIX = "/api/v1/projects"


class TestProjectAPI:
    async def test_create_project(self, async_client, auth_headers):
        """创建项目应返回 201 及 ProjectResp（统一响应格式包裹）。"""
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
        inner = data["data"]
        assert inner["title"] == "我的小说"
        assert inner["author"] == "墨灵作者"
        assert inner["genre"] == "玄幻"
        assert inner["status"] == "draft"
        assert "id" in inner

    async def test_list_projects(self, async_client, auth_headers, test_project):
        """列出项目应返回分页响应（统一响应格式包裹），包含刚创建的项目。"""
        resp = await async_client.get(API_PREFIX, headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        inner = data["data"]
        assert inner["total"] >= 1
        # items 在 data.data 内部
        ids = [item["id"] for item in inner["items"]]
        assert test_project.id in ids

    async def test_get_project_stats(self, async_client, auth_headers, test_project):
        """获取项目统计应返回总项目数/活跃/草稿等计数（统一响应格式包裹）。"""
        resp = await async_client.get(
            f"{API_PREFIX}/stats", headers=auth_headers
        )
        assert resp.status_code == 200
        data = resp.json()
        inner = data["data"]
        assert inner["total_projects"] >= 1
        assert inner["draft_count"] >= 1

    async def test_get_project_detail(self, async_client, auth_headers, test_project):
        """获取单个项目详情应返回 ProjectResp（统一响应格式包裹）。"""
        resp = await async_client.get(
            f"{API_PREFIX}/{test_project.id}", headers=auth_headers
        )
        assert resp.status_code == 200
        data = resp.json()
        inner = data["data"]
        assert inner["id"] == test_project.id
        assert inner["title"] == "测试项目"

    async def test_delete_project(self, async_client, auth_headers, test_project):
        """删除项目应返回 204 No Content（REST 标准删除行为）。"""
        resp = await async_client.delete(
            f"{API_PREFIX}/{test_project.id}", headers=auth_headers
        )
        assert resp.status_code == 204

        # 验证删除后获取不到
        resp2 = await async_client.get(
            f"{API_PREFIX}/{test_project.id}", headers=auth_headers
        )
        assert resp2.status_code == 404
