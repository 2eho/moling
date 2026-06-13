"""墨灵 (Moling) — Auth API 端点测试。

覆盖注册、登录、刷新令牌、获取当前用户、未授权访问。
Windows 兼容版：使用同步 TestClient。
"""

import pytest

API_PREFIX = "/api/v1/auth"

# 辅助函数：从响应中提取数据（适应响应包装格式）
def _get_data(response):
    """从响应中提取数据，处理响应包装格式。"""
    json_data = response.json()
    # 如果响应是包装格式 {code, message, data, meta}，提取 data
    if "data" in json_data and "code" in json_data:
        return json_data["data"]
    return json_data


class TestAuthAPI:
    def test_register(self, client):
        """注册新用户应返回 201 以及 access_token / refresh_token / user。"""
        payload = {
            "email": "newuser@example.com",
            "nickname": "新注册用户",
            "password": "password123",
        }
        resp = client.post(f"{API_PREFIX}/register", json=payload)
        assert resp.status_code == 201
        data = _get_data(resp)
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["user"]["email"] == "newuser@example.com"

    def test_login(self, client, test_user):
        """已注册用户登录应返回 200 及 tokens。"""
        payload = {"email": "test@moling.com", "password": "password123"}
        resp = client.post(f"{API_PREFIX}/login", json=payload)
        assert resp.status_code == 200
        data = _get_data(resp)
        assert "access_token" in data
        assert data["user"]["email"] == "test@moling.com"

    def test_login_wrong_credentials(self, client):
        """错误凭据登录应返回 401。"""
        payload = {"email": "test@moling.com", "password": "wrongpassword"}
        resp = client.post(f"{API_PREFIX}/login", json=payload)
        assert resp.status_code == 401

    def test_refresh_token(self, client, test_user):
        """使用正确的 refresh_token 应返回新的令牌对。"""
        # 先登录获取 token
        login_resp = client.post(
            f"{API_PREFIX}/login",
            json={"email": "test@moling.com", "password": "password123"},
        )
        login_data = _get_data(login_resp)
        refresh_token = login_data["refresh_token"]

        resp = client.post(
            f"{API_PREFIX}/refresh",
            json={"refresh_token": refresh_token},
        )
        assert resp.status_code == 200
        data = _get_data(resp)
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["user"]["email"] == "test@moling.com"

    def test_get_current_user(self, client, auth_headers):
        """获取当前用户信息应返回登录用户的 UserResp。"""
        resp = client.get(f"{API_PREFIX}/me", headers=auth_headers)
        assert resp.status_code == 200
        data = _get_data(resp)
        assert data["email"] == "test@moling.com"
        # UserResp 使用 nickname 字段（validation_alias="username"）
        assert data["nickname"] == "测试用户"

    def test_unauthorized_access(self, client):
        """未携带 token 访问 /me 应返回 401。"""
        resp = client.get(f"{API_PREFIX}/me")
        # FastAPI HTTPBearer(auto_error=True) 默认返回 403，但实际经过依赖链后返回 401
        assert resp.status_code == 401
