"""墨灵 (Moling) — API 集成测试。

测试完整的用户流程和工作流。
"""

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


class TestAuthFlow:
    """测试完整的认证流程：注册 → 登录 → 刷新 Token → 获取用户信息。"""

    async def test_complete_auth_flow(self, async_client: AsyncClient):
        """完整认证流程应全部成功。"""
        # 1. 注册
        register_payload = {
            "email": "flowtest@example.com",
            "nickname": "流程测试用户",
            "password": "TestPassword123!"
        }
        register_resp = await async_client.post(
            "/api/v1/auth/register", 
            json=register_payload
        )
        assert register_resp.status_code == 201
        body = register_resp.json()
        assert body["code"] == 0
        register_data = body["data"]
        assert "access_token" in register_data
        assert "refresh_token" in register_data
        access_token = register_data["access_token"]
        refresh_token = register_data["refresh_token"]

        # 2. 使用 access_token 获取用户信息
        auth_headers = {"Authorization": f"Bearer {access_token}"}
        me_resp = await async_client.get(
            "/api/v1/auth/me", 
            headers=auth_headers
        )
        assert me_resp.status_code == 200
        me_data = me_resp.json()["data"]
        assert me_data["email"] == "flowtest@example.com"

        # 3. 刷新 Token
        refresh_payload = {"refresh_token": refresh_token}
        refresh_resp = await async_client.post(
            "/api/v1/auth/refresh", 
            json=refresh_payload
        )
        assert refresh_resp.status_code == 200
        refresh_data = refresh_resp.json()["data"]
        assert "access_token" in refresh_data
        new_access_token = refresh_data["access_token"]
        assert new_access_token != access_token  # 新 token 应该不同

        # 4. 使用新 token 获取用户信息
        new_auth_headers = {"Authorization": f"Bearer {new_access_token}"}
        me_resp2 = await async_client.get(
            "/api/v1/auth/me", 
            headers=new_auth_headers
        )
        assert me_resp2.status_code == 200


class TestProjectWorkflow:
    """测试完整的项目工作流：创建项目 → 列出项目 → 更新项目 → 删除项目。"""

    async def test_complete_project_workflow(self, async_client: AsyncClient, 
                                            auth_headers, test_user):
        """完整项目工作流应全部成功。"""
        # 1. 创建项目
        create_payload = {
            "title": "工作流测试项目",
            "author": "测试作者",
            "genre": "玄幻",
            "creation_mode": "from_scratch"
        }
        create_resp = await async_client.post(
            "/api/v1/projects", 
            json=create_payload,
            headers=auth_headers
        )
        assert create_resp.status_code == 201
        project_data = create_resp.json()["data"]
        project_id = project_data["id"]
        assert project_data["title"] == "工作流测试项目"

        # 2. 列出项目（应包含刚创建的项目）
        list_resp = await async_client.get(
            "/api/v1/projects", 
            headers=auth_headers
        )
        assert list_resp.status_code == 200
        list_data = list_resp.json()["data"]
        project_ids = [p["id"] for p in list_data["items"]]
        assert project_id in project_ids

        # 3. 获取项目详情
        detail_resp = await async_client.get(
            f"/api/v1/projects/{project_id}", 
            headers=auth_headers
        )
        assert detail_resp.status_code == 200
        detail_data = detail_resp.json()["data"]
        assert detail_data["id"] == project_id

        # 4. 更新项目
        update_payload = {
            "title": "更新后的项目标题",
            "genre": "武侠"
        }
        update_resp = await async_client.put(
            f"/api/v1/projects/{project_id}", 
            json=update_payload,
            headers=auth_headers
        )
        assert update_resp.status_code == 200
        update_data = update_resp.json()["data"]
        assert update_data["title"] == "更新后的项目标题"
        assert update_data["genre"] == "武侠"

        # 5. 删除项目
        delete_resp = await async_client.delete(
            f"/api/v1/projects/{project_id}", 
            headers=auth_headers
        )
        assert delete_resp.status_code == 200

        # 6. 验证删除后获取不到
        not_found_resp = await async_client.get(
            f"/api/v1/projects/{project_id}", 
            headers=auth_headers
        )
        assert not_found_resp.status_code == 404


class TestChapterWorkflow:
    """测试完整的章节工作流：创建章节 → 列出章节 → 更新章节 → 删除章节。"""

    async def test_complete_chapter_workflow(self, async_client: AsyncClient, 
                                            auth_headers, test_project):
        """完整章节工作流应全部成功。"""
        project_id = test_project["id"]

        # 1. 创建章节
        create_payload = {
            "chapter_number": 1,
            "title": "工作流测试章节",
            "content": "这是测试内容。"
        }
        params = {"project_id": project_id}
        create_resp = await async_client.post(
            "/api/v1/chapters", 
            json=create_payload,
            headers=auth_headers,
            params=params
        )
        assert create_resp.status_code == 201
        chapter_data = create_resp.json()["data"]
        chapter_id = chapter_data["id"]

        # 2. 列出章节
        list_resp = await async_client.get(
            "/api/v1/chapters", 
            headers=auth_headers,
            params=params
        )
        assert list_resp.status_code == 200
        list_data = list_resp.json()["data"]
        assert any(c["id"] == chapter_id for c in list_data)

        # 3. 获取章节详情
        detail_resp = await async_client.get(
            f"/api/v1/chapters/{chapter_id}", 
            headers=auth_headers,
            params=params
        )
        assert detail_resp.status_code == 200

        # 4. 更新章节
        update_payload = {
            "title": "更新后的章节标题",
            "content": "更新后的内容。"
        }
        update_resp = await async_client.put(
            f"/api/v1/chapters/{chapter_id}", 
            json=update_payload,
            headers=auth_headers,
            params=params
        )
        assert update_resp.status_code == 200

        # 5. 删除章节
        delete_resp = await async_client.delete(
            f"/api/v1/chapters/{chapter_id}", 
            headers=auth_headers,
            params=params
        )
        assert delete_resp.status_code == 204

        # 6. 验证删除后获取不到
        not_found_resp = await async_client.get(
            f"/api/v1/chapters/{chapter_id}", 
            headers=auth_headers,
            params=params
        )
        assert not_found_resp.status_code == 404


class TestVaultWorkflow:
    """测试完整的四库工作流：创建人物 → 更新人物 → 删除人物。"""

    async def test_complete_vault_character_workflow(self, async_client: AsyncClient, 
                                                     auth_headers, test_project):
        """完整人物库工作流应全部成功。"""
        project_id = test_project["id"]

        # 1. 创建人物
        create_payload = {
            "name": "工作流测试角色",
            "description": "这是一个测试角色。",
            "traits": ["勇敢"]
        }
        params = {"project_id": project_id}
        create_resp = await async_client.post(
            "/api/v1/vault/characters", 
            json=create_payload,
            headers=auth_headers,
            params=params
        )
        assert create_resp.status_code == 201
        character_data = create_resp.json()["data"]
        character_id = character_data["id"]

        # 2. 列出人物
        list_resp = await async_client.get(
            "/api/v1/vault/characters", 
            headers=auth_headers,
            params=params
        )
        assert list_resp.status_code == 200
        list_data = list_resp.json()["data"]
        assert any(c["id"] == character_id for c in list_data)

        # 3. 更新人物
        update_payload = {
            "name": "更新后的角色名",
            "description": "更新后的描述。"
        }
        update_resp = await async_client.put(
            f"/api/v1/vault/characters/{character_id}", 
            json=update_payload,
            headers=auth_headers,
            params=params
        )
        assert update_resp.status_code == 200

        # 4. 删除人物
        delete_resp = await async_client.delete(
            f"/api/v1/vault/characters/{character_id}", 
            headers=auth_headers,
            params=params
        )
        assert delete_resp.status_code == 204
