"""Locust 性能测试 — 墨灵 (Moling) 后端 API."""

import random
from locust import HttpUser, between, task


class MolingUser(HttpUser):
    """模拟真实用户行为：登录 → 查看项目 → 查看章节。"""

    wait_time = between(1, 3)
    token = None
    user_id = None

    def on_start(self):
        """登录获取 token。"""
        email = f"perf_test_{random.randint(1, 1000)}@moling.com"
        password = "Password123!"

        # 先注册（允许失败，用户可能已存在）
        self.client.post(
            "/api/v1/auth/register",
            json={"email": email, "nickname": "压测用户", "password": password},
            name="register",
        )

        # 登录
        resp = self.client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": password},
            name="login",
        )
        if resp.status_code == 200:
            data = resp.json()
            # 适配统一响应格式 {code, message, data}
            inner = data.get("data", data)
            token = inner.get("access_token")
            if token:
                self.token = token
                self.headers = {"Authorization": f"Bearer {token}"}
            else:
                self.token = None
                self.headers = {}

    @task(3)
    def list_projects(self):
        """查看项目列表（权重 3）。"""
        if not self.token:
            return
        self.client.get(
            "/api/v1/projects",
            headers=self.headers,
            name="list_projects",
        )

    @task(2)
    def get_project_stats(self):
        """查看项目统计（权重 2）。"""
        if not self.token:
            return
        # 先获取项目列表取第一个 id
        resp = self.client.get(
            "/api/v1/projects",
            headers=self.headers,
            name="list_projects_for_stats",
        )
        if resp.status_code == 200:
            data = resp.json()
            inner = data.get("data", data)
            projects = inner.get("projects", [])
            if projects:
                project_id = projects[0].get("id")
                self.client.get(
                    f"/api/v1/projects/{project_id}",
                    headers=self.headers,
                    name="get_project_detail",
                )

    @task(1)
    def refresh_token(self):
        """刷新 Token（权重 1）。"""
        if not self.token:
            return
        # 需要先获取 refresh_token（简化版暂不实现）
        pass
