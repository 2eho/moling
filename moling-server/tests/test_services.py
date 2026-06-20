"""墨灵 (Moling) — 服务层测试。

覆盖 AuthService 和 ProjectService 的核心业务逻辑。
"""

import pytest

pytestmark = pytest.mark.asyncio


# ============================================================================
# AuthService
# ============================================================================


class TestAuthService:
    async def test_register_success(self, test_db):
        """注册新用户成功，返回包含 access_token / refresh_token / user 的 TokenResp。"""
        from app.schemas.auth import RegisterReq
        from app.service import auth_service

        req = RegisterReq(
            email="new@example.com",
            nickname="新用户",
            password="password123",
        )
        result = await auth_service.register(test_db, req)

        assert result.user.email == "new@example.com"
        assert result.user.nickname == "新用户"
        assert result.access_token is not None
        assert result.refresh_token is not None
        assert result.user.id is not None

    async def test_register_duplicate_email(self, test_db, test_user):
        """重复邮箱注册应抛出 ConflictError。"""
        from app.errors import ConflictError
        from app.schemas.auth import RegisterReq
        from app.service import auth_service

        req = RegisterReq(
            email="testuser@example.com",
            nickname="另一个用户",
            password="password123",
        )
        with pytest.raises(ConflictError):
            await auth_service.register(test_db, req)

    async def test_register_duplicate_username(self, test_db, test_user):
        """重复用户名注册应抛出 ConflictError。"""
        from app.errors import ConflictError
        from app.schemas.auth import RegisterReq
        from app.service import auth_service

        req = RegisterReq(
            email="other@moling.com",
            nickname="测试用户",
            password="password123",
        )
        with pytest.raises(ConflictError):
            await auth_service.register(test_db, req)

    async def test_login_success(self, test_db, test_user):
        """使用正确邮箱密码登录成功，返回 TokenResp。"""
        from app.schemas.auth import LoginReq
        from app.service import auth_service

        req = LoginReq(email="testuser@example.com", password="TestPassword123!")
        result = await auth_service.login(test_db, req)

        assert result.user.email == "testuser@example.com"
        assert result.access_token is not None

    async def test_login_wrong_password(self, test_db, test_user):
        """密码错误应抛出 AuthError。"""
        from app.errors import AuthError
        from app.schemas.auth import LoginReq
        from app.service import auth_service

        req = LoginReq(email="testuser@example.com", password="wrongpassword")
        with pytest.raises(AuthError):
            await auth_service.login(test_db, req)

    async def test_login_nonexistent_user(self, test_db):
        """不存在的用户登录应抛出 AuthError。"""
        from app.errors import AuthError
        from app.schemas.auth import LoginReq
        from app.service import auth_service

        req = LoginReq(email="noone@moling.com", password="password123")
        with pytest.raises(AuthError):
            await auth_service.login(test_db, req)


# ============================================================================
# ProjectService
# ============================================================================


class TestProjectService:
    async def test_create_project(self, test_db, test_user):
        """创建项目成功，返回 ProjectResp。"""
        from app.schemas.project import CreateProjectReq
        from app.service import project_service

        req = CreateProjectReq(
            title="新项目",
            author="作者",
            genre="科幻",
            creation_mode="from_scratch",
        )
        project = await project_service.create_project(
            test_db, user_id=test_user.user.id, req=req
        )

        assert project.title == "新项目"
        assert project.author == "作者"
        assert project.genre == "科幻"
        assert project.status == "draft"
        assert project.id is not None

    async def test_list_user_projects(self, test_db, test_user, test_project):
        """列出用户的项目列表，应包含刚创建的项目。"""
        from app.service import project_service

        result = await project_service.list_projects(test_db, test_user.id)
        projects = result["items"]
        assert len(projects) >= 1
        ids = [p.id for p in projects]
        assert test_project.id in ids

    async def test_get_project(self, test_db, test_user, test_project):
        """获取项目详情成功。"""
        from app.service import project_service

        project = await project_service.get_project(
            test_db, test_user.id, test_project.id
        )
        assert project.id == test_project.id
        assert project.title == "测试项目"

    async def test_get_project_not_found(self, test_db, test_user):
        """不存在的项目应抛出 NotFoundError。"""
        from app.errors import NotFoundError
        from app.service import project_service

        with pytest.raises(NotFoundError):
            await project_service.get_project(test_db, test_user.id, 99999)

    async def test_delete_project(self, test_db, test_user, test_project):
        """删除项目后，再次获取应抛出 NotFoundError。"""
        from app.errors import NotFoundError
        from app.service import project_service

        await project_service.delete_project(
            test_db, test_user.id, test_project.id
        )

        with pytest.raises(NotFoundError):
            await project_service.get_project(
                test_db, test_user.id, test_project.id
            )

    async def test_get_project_stats(self, test_db, test_user, test_project):
        """获取项目统计信息。"""
        from app.service import project_service

        stats = await project_service.get_project_stats(test_db, test_user.id)
        assert stats.total_projects >= 1
        assert stats.draft_count >= 1
