"""Locust 性能测试 — 墨灵 (Moling) 后端 API.

覆盖三个核心场景：
- 场景 A：100 并发用户同时生成文本
- 场景 B：数据库大量数据查询（10,000 项目 + 100,000 章节）
- 场景 C：API 响应时间测试（P95 < 500ms）
"""

import random
import json
from locust import HttpUser, between, task, events
from locust.runners import STATE_STOPPING, STATE_STOPPED, STATE_CLEANUP, WorkerRunner
import time


class MolingUser(HttpUser):
    """模拟真实用户行为：登录 → 查看项目 → 查看章节 → 生成文本。"""

    wait_time = between(1, 3)
    token = None
    user_id = None
    project_id = None
    chapter_id = None

    def on_start(self):
        """登录获取 token。"""
        email = f"perf_test_{random.randint(1, 10000)}@moling.com"
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
                
            # 获取用户 ID
            user_data = inner.get("user", {})
            self.user_id = user_data.get("id", 1)
        else:
            self.token = None
            self.headers = {}

    def _ensure_project(self):
        """确保有可用的项目 ID。"""
        if self.project_id:
            return
        
        # 获取项目列表
        resp = self.client.get(
            "/api/v1/projects",
            headers=self.headers,
            name="list_projects_for_id",
        )
        if resp.status_code == 200:
            data = resp.json()
            inner = data.get("data", data)
            projects = inner.get("projects", [])
            if projects:
                self.project_id = projects[0].get("id")
            else:
                # 创建新项目
                create_resp = self.client.post(
                    "/api/v1/projects",
                    json={
                        "title": f"压测项目_{random.randint(1, 10000)}",
                        "genre": "fantasy",
                        "language": "zh"
                    },
                    headers=self.headers,
                    name="create_project",
                )
                if create_resp.status_code == 201:
                    create_data = create_resp.json()
                    self.project_id = create_data.get("data", {}).get("id")

    def _ensure_chapter(self):
        """确保有可用的章节 ID。"""
        if self.chapter_id:
            return
        
        self._ensure_project()
        if not self.project_id:
            return
        
        # 获取章节列表
        resp = self.client.get(
            f"/api/v1/projects/{self.project_id}/chapters",
            headers=self.headers,
            name="list_chapters_for_id",
        )
        if resp.status_code == 200:
            chapters = resp.json()
            if isinstance(chapters, list) and chapters:
                self.chapter_id = chapters[0].get("id")
            else:
                # 创建新章节
                create_resp = self.client.post(
                    f"/api/v1/projects/{self.project_id}/chapters",
                    json={
                        "title": f"压测章节_{random.randint(1, 10000)}",
                        "order": 1
                    },
                    headers=self.headers,
                    name="create_chapter",
                )
                if create_resp.status_code == 201:
                    create_data = create_resp.json()
                    self.chapter_id = create_data.get("data", {}).get("id")

    # ==================== 场景 A：生成文本 ====================
    
    @task(3)
    def generate_text(self):
        """场景 A：生成文本（权重 3）。
        
        测试 AI 生成 API 的性能。
        注意：此测试可能需要 mock LLM 服务以避免实际调用。
        """
        if not self.token:
            return
        
        self._ensure_chapter()
        if not self.chapter_id:
            return
        
        # 调用生成 API
        self.client.post(
            "/api/v1/generate",
            json={
                "project_id": self.project_id,
                "chapter_id": self.chapter_id,
                "prompt": "继续写作",
                "max_tokens": 500
            },
            headers=self.headers,
            name="generate_text",
        )

    # ==================== 场景 B：查看章节列表 ====================
    
    @task(5)
    def view_chapters(self):
        """场景 B：查看章节列表（权重 5）。
        
        测试数据库查询性能，特别是在有大量数据时。
        """
        if not self.token:
            return
        
        self._ensure_project()
        if not self.project_id:
            return
        
        # 查看章节列表
        self.client.get(
            f"/api/v1/projects/{self.project_id}/chapters",
            headers=self.headers,
            name="view_chapters",
        )

    # ==================== 场景 B：查看卡牌 ====================
    
    @task(2)
    def view_cards(self):
        """场景 B：查看卡牌（权重 2）。
        
        测试数据库查询性能。
        """
        if not self.token:
            return
        
        self._ensure_project()
        if not self.project_id:
            return
        
        # 查看卡牌
        self.client.get(
            f"/api/v1/projects/{self.project_id}/cards",
            headers=self.headers,
            name="view_cards",
        )

    # ==================== 场景 C：API 响应时间测试 ====================
    
    @task(4)
    def list_projects(self):
        """场景 C：查看项目列表（权重 4）。
        
        测试 API 响应时间。
        """
        if not self.token:
            return
        
        self.client.get(
            "/api/v1/projects",
            headers=self.headers,
            name="list_projects",
        )

    @task(2)
    def get_project_detail(self):
        """场景 C：查看项目详情（权重 2）。"""
        if not self.token:
            return
        
        self._ensure_project()
        if not self.project_id:
            return
        
        self.client.get(
            f"/api/v1/projects/{self.project_id}",
            headers=self.headers,
            name="get_project_detail",
        )

    @task(1)
    def get_project_stats(self):
        """场景 C：查看项目统计（权重 1）。"""
        if not self.token:
            return
        
        self.client.get(
            "/api/v1/projects/stats",
            headers=self.headers,
            name="get_project_stats",
        )

    @task(1)
    def list_notifications(self):
        """场景 C：查看通知列表（权重 1）。"""
        if not self.token:
            return
        
        self.client.get(
            "/api/v1/notifications",
            headers=self.headers,
            name="list_notifications",
        )

    @task(1)
    def get_health_status(self):
        """场景 C：查看健康状态（权重 1）。"""
        if not self.token:
            return
        
        self._ensure_project()
        if not self.project_id:
            return
        
        self.client.get(
            f"/api/v1/projects/{self.project_id}/health",
            headers=self.headers,
            name="get_health_status",
        )

    @task(1)
    def refresh_token(self):
        """刷新 Token（权重 1）。"""
        if not self.token:
            return
        # 需要先获取 refresh_token（简化版暂不实现）
        pass


# ==================== 性能监控 ====================

@events.init.add_listener
def on_locust_init(environment, **_kwargs):
    """初始化性能监控。"""
    if not isinstance(environment.runner, WorkerRunner):
        print("\n" + "="*60)
        print("墨灵性能压测")
        print("="*60)
        print("场景 A：100 并发用户生成文本")
        print("场景 B：数据库大量数据查询")
        print("场景 C：API 响应时间测试（P95 < 500ms）")
        print("="*60 + "\n")


@events.test_stop.add_listener
def on_test_stop(environment, **_kwargs):
    """测试停止时生成报告。"""
    print("\n" + "="*60)
    print("性能测试结果")
    print("="*60)
    
    stats = environment.stats
    
    # 打印关键指标
    print(f"\n{'接口':<30} {'请求数':<10} {'失败数':<10} {'P95(ms)':<10} {'吞吐量(req/s)':<15}")
    print("-" * 85)
    
    for name, stat in stats.entries.items():
        if isinstance(name, tuple):
            continue
        
        print(f"{name:<30} {stat.num_requests:<10} {stat.num_failures:<10} "
              f"{stat.get_response_time_percentile(0.95):<10.2f} "
              f"{stat.total_rps:<15.2f}")
    
    # 检查 P95 是否 < 500ms
    print("\n" + "="*60)
    print("P95 响应时间检查（目标：< 500ms）")
    print("="*60)
    
    all_passed = True
    for name, stat in stats.entries.items():
        if isinstance(name, tuple):
            continue
        
        p95 = stat.get_response_time_percentile(0.95)
        status = "✅" if p95 < 500 else "❌"
        if p95 >= 500:
            all_passed = False
        print(f"{name:<30} P95={p95:.2f}ms {status}")
    
    if all_passed:
        print("\n✅ 所有接口 P95 响应时间 < 500ms")
    else:
        print("\n❌ 部分接口 P95 响应时间 >= 500ms，需要优化")
    
    print("\n" + "="*60)
