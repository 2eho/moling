"""墨灵 (Moling) — Health Check API 端点测试。"""

import pytest

pytestmark = pytest.mark.asyncio


class TestHealthAPI:
    async def test_health_check(self, async_client):
        """健康检查端点应返回 200 及服务状态信息。"""
        resp = await async_client.get("/api/v1/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] in ("ok", "degraded")
        assert "version" in data
        assert "timestamp" in data
        assert "database" in data
