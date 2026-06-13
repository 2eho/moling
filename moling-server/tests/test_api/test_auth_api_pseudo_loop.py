"""墨灵 (Moling) — 认证 API 伪环路测试。

使用 unittest.mock 来 mock 数据库会话和认证服务，
直接测试 API 端点的逻辑，验证请求/响应格式，
模拟各种边界情况。

此测试方案绕过 Windows 上的 greenlet DLL 问题。
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app
from app.schemas.auth import TokenResp, UserResp


# ---------------------------------------------------------------------------
# 测试客户端固件
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def pseudo_client():
    """创建测试客户端，禁用 lifespan 以避免数据库连接。
    
    使用 pseudo_client 而不是 client，以避免被 conftest.py 的
    pytest_collection_modifyitems 跳过（Windows 上会跳过使用 client fixture 的测试）。
    """
    with patch("app.main.lifespan"):
        with TestClient(app) as c:
            yield c


# ---------------------------------------------------------------------------
# 测试数据
# ---------------------------------------------------------------------------

REGISTER_DATA = {
    "email": "test@example.com",
    "nickname": "testuser",
    "password": "TestPass123!",
}

LOGIN_DATA = {
    "email": "test@example.com",
    "password": "TestPass123!",
}

REFRESH_DATA = {
    "refresh_token": "fake-refresh-token",
}

MOCK_USER_ID = "550e8400-e29b-41d4-a716-446655440000"
MOCK_ACCESS_TOKEN = "fake-access-token"
MOCK_REFRESH_TOKEN = "fake-refresh-token"


# ---------------------------------------------------------------------------
# Mock 辅助函数
# ---------------------------------------------------------------------------

def create_mock_user():
    """创建模拟用户对象。"""
    mock_user = MagicMock()
    mock_user.id = MOCK_USER_ID
    mock_user.email = "test@example.com"
    mock_user.username = "testuser"
    mock_user.password_hash = "hashed_password"
    mock_user.avatar_url = None
    mock_user.status = "active"
    mock_user.created_at = "2024-01-01T00:00:00"
    mock_user.updated_at = "2024-01-01T00:00:00"
    return mock_user


def create_mock_token_resp():
    """创建模拟令牌响应。"""
    mock_user = create_mock_user()
    return {
        "access_token": MOCK_ACCESS_TOKEN,
        "refresh_token": MOCK_REFRESH_TOKEN,
        "token_type": "bearer",
        "expires_in": 900,
        "user": {
            "id": MOCK_USER_ID,
            "email": "test@example.com",
            "nickname": "testuser",
            "avatar_url": None,
            "status": "active",
            "created_at": "2024-01-01T00:00:00",
            "updated_at": "2024-01-01T00:00:00",
        },
    }


# ---------------------------------------------------------------------------
# 注册 API 测试
# ---------------------------------------------------------------------------


class TestRegisterAPI:
    """注册 API 端点测试。"""

    @patch("app.router.auth.auth_service")
    def test_register_success(self, mock_auth_service, pseudo_client):
        """测试注册成功场景。"""
        # 模拟 auth_service.register 返回成功响应
        mock_auth_service.register = AsyncMock(
            return_value=TokenResp(
                access_token=MOCK_ACCESS_TOKEN,
                refresh_token=MOCK_REFRESH_TOKEN,
                token_type="bearer",
                expires_in=900,
                user=UserResp(
                    id=MOCK_USER_ID,
                    email="test@example.com",
                    username="testuser",  # 使用 username 而不是 nickname
                    avatar_url=None,
                    status="active",
                    created_at="2024-01-01T00:00:00",
                    updated_at="2024-01-01T00:00:00",
                ),
            )
        )

        response = pseudo_client.post("/api/v1/auth/register", json=REGISTER_DATA)

        assert response.status_code == 201
        data = response.json()
        assert "access_token" in data
        assert "token_type" in data
        assert data["token_type"] == "bearer"

    @patch("app.router.auth.auth_service")
    def test_register_duplicate_email(self, mock_auth_service, pseudo_client):
        """测试注册失败 - 重复邮箱。"""
        from app.errors import ConflictError, ErrorCode

        # 模拟 auth_service.register 抛出冲突异常
        mock_auth_service.register = AsyncMock(
            side_effect=ConflictError(
                error_code=ErrorCode.USER_EMAIL_EXISTS,
                detail="Email already registered",
            )
        )

        response = pseudo_client.post("/api/v1/auth/register", json=REGISTER_DATA)

        assert response.status_code == 409

    @patch("app.router.auth.auth_service")
    def test_register_duplicate_username(self, mock_auth_service, pseudo_client):
        """测试注册失败 - 重复用户名。"""
        from app.errors import ConflictError, ErrorCode

        # 模拟 auth_service.register 抛出用户名冲突异常
        mock_auth_service.register = AsyncMock(
            side_effect=ConflictError(
                error_code=ErrorCode.USER_USERNAME_EXISTS,
                detail="Username already taken",
            )
        )

        response = pseudo_client.post("/api/v1/auth/register", json=REGISTER_DATA)

        assert response.status_code == 409

    def test_register_invalid_email(self, pseudo_client):
        """测试注册失败 - 无效邮箱格式。"""
        invalid_data = REGISTER_DATA.copy()
        invalid_data["email"] = "not-an-email"

        response = pseudo_client.post("/api/v1/auth/register", json=invalid_data)

        assert response.status_code == 422  # Validation error

    def test_register_short_password(self, pseudo_client):
        """测试注册失败 - 密码太短。"""
        invalid_data = REGISTER_DATA.copy()
        invalid_data["password"] = "123"

        response = pseudo_client.post("/api/v1/auth/register", json=invalid_data)

        assert response.status_code == 422  # Validation error


# ---------------------------------------------------------------------------
# 登录 API 测试
# ---------------------------------------------------------------------------


class TestLoginAPI:
    """登录 API 端点测试。"""

    @patch("app.router.auth.auth_service")
    def test_login_success(self, mock_auth_service, pseudo_client):
        """测试登录成功场景。"""
        # 模拟 auth_service.login 返回成功响应
        mock_auth_service.login = AsyncMock(
            return_value=TokenResp(
                access_token=MOCK_ACCESS_TOKEN,
                refresh_token=MOCK_REFRESH_TOKEN,
                token_type="bearer",
                expires_in=900,
                user=UserResp(
                    id=MOCK_USER_ID,
                    email="test@example.com",
                    username="testuser",
                    avatar_url=None,
                    status="active",
                    created_at="2024-01-01T00:00:00",
                    updated_at="2024-01-01T00:00:00",
                ),
            )
        )

        response = pseudo_client.post("/api/v1/auth/login", json=LOGIN_DATA)

        assert response.status_code == 200
        data = response.json()
        assert data["access_token"] == MOCK_ACCESS_TOKEN
        assert data["token_type"] == "bearer"

    @patch("app.router.auth.auth_service")
    def test_login_wrong_password(self, mock_auth_service, pseudo_client):
        """测试登录失败 - 错误密码。"""
        from app.errors import AuthError, ErrorCode

        # 模拟 auth_service.login 抛出认证异常
        mock_auth_service.login = AsyncMock(
            side_effect=AuthError(
                error_code=ErrorCode.AUTH_INVALID_CREDENTIALS,
                detail="Invalid email or password",
            )
        )

        response = pseudo_client.post("/api/v1/auth/login", json=LOGIN_DATA)

        assert response.status_code == 401

    @patch("app.router.auth.auth_service")
    def test_login_user_not_found(self, mock_auth_service, pseudo_client):
        """测试登录失败 - 用户不存在。"""
        from app.errors import AuthError, ErrorCode

        # 模拟 auth_service.login 抛出认证异常（用户不存在）
        mock_auth_service.login = AsyncMock(
            side_effect=AuthError(
                error_code=ErrorCode.AUTH_INVALID_CREDENTIALS,
                detail="Invalid email or password",
            )
        )

        response = pseudo_client.post("/api/v1/auth/login", json=LOGIN_DATA)

        assert response.status_code == 401

    def test_login_invalid_email(self, pseudo_client):
        """测试登录失败 - 无效邮箱格式。"""
        invalid_data = LOGIN_DATA.copy()
        invalid_data["email"] = "not-an-email"

        response = pseudo_client.post("/api/v1/auth/login", json=invalid_data)

        assert response.status_code == 422  # Validation error

    @patch("app.router.auth.auth_service")
    def test_login_inactive_user(self, mock_auth_service, pseudo_client):
        """测试登录失败 - 用户账户禁用。"""
        from app.errors import AuthError, ErrorCode

        # 模拟 auth_service.login 抛出权限异常（账户禁用）
        mock_auth_service.login = AsyncMock(
            side_effect=AuthError(
                error_code=ErrorCode.AUTH_INSUFFICIENT_PERMISSIONS,
                detail="Account is disabled",
            )
        )

        response = pseudo_client.post("/api/v1/auth/login", json=LOGIN_DATA)

        assert response.status_code == 403  # AUTH_INSUFFICIENT_PERMISSIONS 返回 403


# ---------------------------------------------------------------------------
# 刷新令牌 API 测试
# ---------------------------------------------------------------------------


class TestRefreshAPI:
    """刷新令牌 API 端点测试。"""

    @patch("app.router.auth.auth_service")
    def test_refresh_success(self, mock_auth_service, pseudo_client):
        """测试刷新令牌成功场景。"""
        # 模拟 auth_service.refresh_tokens 返回成功响应
        mock_auth_service.refresh_tokens = AsyncMock(
            return_value=TokenResp(
                access_token="new-access-token",
                refresh_token="new-refresh-token",
                token_type="bearer",
                expires_in=900,
                user=UserResp(
                    id=MOCK_USER_ID,
                    email="test@example.com",
                    username="testuser",
                    avatar_url=None,
                    status="active",
                    created_at="2024-01-01T00:00:00",
                    updated_at="2024-01-01T00:00:00",
                ),
            )
        )

        response = pseudo_client.post("/api/v1/auth/refresh", json=REFRESH_DATA)

        assert response.status_code == 200
        data = response.json()
        assert data["access_token"] == "new-access-token"
        assert data["token_type"] == "bearer"

    @patch("app.router.auth.auth_service")
    def test_refresh_invalid_token(self, mock_auth_service, pseudo_client):
        """测试刷新失败 - 无效刷新令牌。"""
        from app.errors import AuthError, ErrorCode

        # 模拟 auth_service.refresh_tokens 抛出认证异常
        mock_auth_service.refresh_tokens = AsyncMock(
            side_effect=AuthError(
                error_code=ErrorCode.AUTH_INVALID_TOKEN,
                detail="Invalid refresh token",
            )
        )

        response = pseudo_client.post("/api/v1/auth/refresh", json=REFRESH_DATA)

        assert response.status_code == 401

    def test_refresh_missing_token(self, pseudo_client):
        """测试刷新失败 - 缺少刷新令牌。"""
        response = pseudo_client.post("/api/v1/auth/refresh", json={})

        assert response.status_code == 422  # Validation error


# ---------------------------------------------------------------------------
# 获取当前用户 API 测试
# ---------------------------------------------------------------------------


class TestGetMeAPI:
    """获取当前用户 API 端点测试。"""

    @patch("app.router.auth.jwt.decode")
    @patch("app.router.auth.auth_service")
    def test_get_me_success(self, mock_auth_service, mock_jwt_decode, pseudo_client):
        """测试获取当前用户信息成功。"""
        # 模拟 JWT decode 返回有效 payload
        mock_jwt_decode.return_value = {"sub": MOCK_USER_ID, "type": "access"}
        
        # 模拟 auth_service.get_current_user 返回用户信息
        mock_auth_service.get_current_user = AsyncMock(
            return_value=UserResp(
                id=MOCK_USER_ID,
                email="test@example.com",
                username="testuser",
                avatar_url=None,
                status="active",
                created_at="2024-01-01T00:00:00",
                updated_at="2024-01-01T00:00:00",
            )
        )

        headers = {"Authorization": f"Bearer {MOCK_ACCESS_TOKEN}"}
        response = pseudo_client.get("/api/v1/auth/me", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "test@example.com"
        assert data["nickname"] == "testuser"

    def test_get_me_unauthorized(self, pseudo_client):
        """测试获取当前用户失败 - 未提供令牌。"""
        response = pseudo_client.get("/api/v1/auth/me")

        assert response.status_code == 401  # HTTPBearer auto_error=True 返回 401

    @patch("app.router.auth.auth_service")
    def test_get_me_invalid_token(self, mock_auth_service, pseudo_client):
        """测试获取当前用户失败 - 无效令牌。"""
        headers = {"Authorization": "Bearer invalid-token"}
        response = pseudo_client.get("/api/v1/auth/me", headers=headers)

        assert response.status_code == 401

    @patch("app.router.auth.jwt.decode")
    @patch("app.router.auth.auth_service")
    def test_get_me_user_not_found(self, mock_auth_service, mock_jwt_decode, pseudo_client):
        """测试获取当前用户失败 - 用户不存在。"""
        from app.errors import NotFoundError, ErrorCode

        # 模拟 JWT decode 返回有效 payload
        mock_jwt_decode.return_value = {"sub": MOCK_USER_ID, "type": "access"}
        
        # 模拟 auth_service.get_current_user 抛出未找到异常
        mock_auth_service.get_current_user = AsyncMock(
            side_effect=NotFoundError(
                error_code=ErrorCode.USER_NOT_FOUND,
                detail="User not found",
            )
        )

        headers = {"Authorization": f"Bearer {MOCK_ACCESS_TOKEN}"}
        response = pseudo_client.get("/api/v1/auth/me", headers=headers)

        assert response.status_code == 404


# ---------------------------------------------------------------------------
# 集成场景测试
# ---------------------------------------------------------------------------


class TestAuthIntegration:
    """认证 API 集成场景测试。"""

    @patch("app.router.auth.auth_service")
    def test_register_then_login(self, mock_auth_service, pseudo_client):
        """测试注册后登录的完整流程。"""
        # 模拟注册成功
        mock_auth_service.register = AsyncMock(
            return_value=TokenResp(
                access_token=MOCK_ACCESS_TOKEN,
                refresh_token=MOCK_REFRESH_TOKEN,
                token_type="bearer",
                expires_in=900,
                user=UserResp(
                    id=MOCK_USER_ID,
                    email="test@example.com",
                    username="testuser",
                    avatar_url=None,
                    status="active",
                    created_at="2024-01-01T00:00:00",
                    updated_at="2024-01-01T00:00:00",
                ),
            )
        )

        # 模拟登录成功
        mock_auth_service.login = AsyncMock(
            return_value=TokenResp(
                access_token="new-access-token",
                refresh_token="new-refresh-token",
                token_type="bearer",
                expires_in=900,
                user=UserResp(
                    id=MOCK_USER_ID,
                    email="test@example.com",
                    username="testuser",
                    avatar_url=None,
                    status="active",
                    created_at="2024-01-01T00:00:00",
                    updated_at="2024-01-01T00:00:00",
                ),
            )
        )

        # 1. 注册
        register_resp = pseudo_client.post("/api/v1/auth/register", json=REGISTER_DATA)
        assert register_resp.status_code == 201

        # 2. 登录
        login_resp = pseudo_client.post("/api/v1/auth/login", json=LOGIN_DATA)
        assert login_resp.status_code == 200
        data = login_resp.json()
        assert data["access_token"] == "new-access-token"

    @patch("app.router.auth.auth_service")
    def test_login_then_refresh(self, mock_auth_service, pseudo_client):
        """测试登录后刷新令牌的完整流程。"""
        # 模拟登录成功
        mock_auth_service.login = AsyncMock(
            return_value=TokenResp(
                access_token=MOCK_ACCESS_TOKEN,
                refresh_token=MOCK_REFRESH_TOKEN,
                token_type="bearer",
                expires_in=900,
                user=UserResp(
                    id=MOCK_USER_ID,
                    email="test@example.com",
                    username="testuser",
                    avatar_url=None,
                    status="active",
                    created_at="2024-01-01T00:00:00",
                    updated_at="2024-01-01T00:00:00",
                ),
            )
        )

        # 模拟刷新成功
        mock_auth_service.refresh_tokens = AsyncMock(
            return_value=TokenResp(
                access_token="refreshed-access-token",
                refresh_token="refreshed-refresh-token",
                token_type="bearer",
                expires_in=900,
                user=UserResp(
                    id=MOCK_USER_ID,
                    email="test@example.com",
                    username="testuser",
                    avatar_url=None,
                    status="active",
                    created_at="2024-01-01T00:00:00",
                    updated_at="2024-01-01T00:00:00",
                ),
            )
        )

        # 1. 登录
        login_resp = pseudo_client.post("/api/v1/auth/login", json=LOGIN_DATA)
        assert login_resp.status_code == 200
        login_data = login_resp.json()
        refresh_token = login_data["refresh_token"]

        # 2. 刷新令牌
        refresh_resp = pseudo_client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token},
        )
        assert refresh_resp.status_code == 200
        refresh_data = refresh_resp.json()
        assert refresh_data["access_token"] == "refreshed-access-token"

    @patch("app.router.auth.jwt.decode")
    @patch("app.router.auth.auth_service")
    def test_login_then_get_me(self, mock_auth_service, mock_jwt_decode, pseudo_client):
        """测试登录后获取当前用户的完整流程。"""
        # 模拟 JWT decode 返回有效 payload
        mock_jwt_decode.return_value = {"sub": MOCK_USER_ID, "type": "access"}
        
        # 模拟登录成功
        mock_auth_service.login = AsyncMock(
            return_value=TokenResp(
                access_token=MOCK_ACCESS_TOKEN,
                refresh_token=MOCK_REFRESH_TOKEN,
                token_type="bearer",
                expires_in=900,
                user=UserResp(
                    id=MOCK_USER_ID,
                    email="test@example.com",
                    username="testuser",
                    avatar_url=None,
                    status="active",
                    created_at="2024-01-01T00:00:00",
                    updated_at="2024-01-01T00:00:00",
                ),
            )
        )

        # 模拟获取当前用户成功
        mock_auth_service.get_current_user = AsyncMock(
            return_value=UserResp(
                id=MOCK_USER_ID,
                email="test@example.com",
                username="testuser",
                avatar_url=None,
                status="active",
                created_at="2024-01-01T00:00:00",
                updated_at="2024-01-01T00:00:00",
            )
        )

        # 1. 登录
        login_resp = pseudo_client.post("/api/v1/auth/login", json=LOGIN_DATA)
        assert login_resp.status_code == 200
        login_data = login_resp.json()
        access_token = login_data["access_token"]

        # 2. 获取当前用户
        headers = {"Authorization": f"Bearer {access_token}"}
        me_resp = pseudo_client.get("/api/v1/auth/me", headers=headers)
        assert me_resp.status_code == 200
        me_data = me_resp.json()
        assert me_data["email"] == "test@example.com"
