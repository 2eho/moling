#!/usr/bin/env python3
"""墨灵性能测试 — 使用 requests 库的简化性能测试.

此脚本不依赖 Locust，使用 requests 库进行性能测试。
适用于 Locust 安装失败或需要快速测试的场景。

使用方法：
    python simple_performance_test.py --users 10 --requests 100
    python simple_performance_test.py --all  # 运行所有测试场景
"""

import argparse
import json
import sys
import time
import requests
from datetime import datetime
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import defaultdict


class SimplePerformanceTest:
    """简化性能测试工具."""

    def __init__(self, base_url="http://localhost:8000", output_file="performance_report.json"):
        self.base_url = base_url
        self.output_file = output_file
        self.results = []
        self.token = None
        self.headers = {}

    def register_and_login(self):
        """注册并登录获取 token."""
        print("注册并登录...")
        
        email = f"perf_test_{int(time.time())}@moling.com"
        password = "Password123!"
        
        # 注册
        try:
            resp = requests.post(
                f"{self.base_url}/api/v1/auth/register",
                json={"email": email, "nickname": "性能测试用户", "password": password},
                timeout=10,
            )
            print(f"  注册: {resp.status_code}")
        except Exception as e:
            print(f"  注册失败: {e}")
        
        # 登录
        try:
            resp = requests.post(
                f"{self.base_url}/api/v1/auth/login",
                json={"email": email, "password": password},
                timeout=10,
            )
            if resp.status_code == 200:
                data = resp.json()
                inner = data.get("data", data)
                token = inner.get("access_token")
                if token:
                    self.token = token
                    self.headers = {"Authorization": f"Bearer {token}"}
                    print(f"  ✅ 登录成功")
                    return True
            print(f"  ❌ 登录失败: {resp.status_code}")
        except Exception as e:
            print(f"  ❌ 登录失败: {e}")
        
        return False

    def make_request(self, method, endpoint, json_data=None, name="request"):
        """发送单个请求并记录结果."""
        start_time = time.time()
        result = {
            "endpoint": endpoint,
            "name": name,
            "method": method,
            "status_code": 0,
            "response_time_ms": 0,
            "success": False,
            "error": None,
        }
        
        try:
            if method == "GET":
                resp = requests.get(
                    f"{self.base_url}{endpoint}",
                    headers=self.headers,
                    timeout=30,
                )
            elif method == "POST":
                resp = requests.post(
                    f"{self.base_url}{endpoint}",
                    json=json_data,
                    headers=self.headers,
                    timeout=30,
                )
            else:
                raise ValueError(f"不支持的 HTTP 方法: {method}")
            
            result["status_code"] = resp.status_code
            result["success"] = 200 <= resp.status_code < 300
            
        except Exception as e:
            result["error"] = str(e)
        
        result["response_time_ms"] = (time.time() - start_time) * 1000
        return result

    def run_scenario_a(self, num_users=10, requests_per_user=10):
        """场景 A：并发用户生成文本."""
        print(f"\n{'='*60}")
        print(f"场景 A：并发用户生成文本")
        print(f"{'='*60}")
        print(f"配置: {num_users} 用户 × {requests_per_user} 请求 = {num_users * requests_per_user} 总请求")
        
        # 先确保有项目和章节
        print("\n准备测试数据...")
        project_resp = self.make_request("POST", "/api/v1/projects", {
            "title": f"性能测试项目_{int(time.time())}",
            "genre": "fantasy",
            "language": "zh"
        }, "create_project")
        
        if not project_resp["success"]:
            print("❌ 创建项目失败，跳过场景 A")
            return []
        
        project_id = json.loads(project_resp.get("response", "{}")).get("data", {}).get("id", 1)
        
        chapter_resp = self.make_request("POST", f"/api/v1/projects/{project_id}/chapters", {
            "title": "性能测试章节",
            "order": 1
        }, "create_chapter")
        
        if not chapter_resp["success"]:
            print("❌ 创建章节失败，跳过场景 A")
            return []
        
        chapter_id = json.loads(chapter_resp.get("response", "{}")).get("data", {}).get("id", 1)
        
        # 并发发送请求
        print(f"\n发送请求（并发）...")
        scenario_results = []
        
        def send_generate_request(_):
            return self.make_request(
                "POST",
                "/api/v1/generate",
                {
                    "project_id": project_id,
                    "chapter_id": chapter_id,
                    "prompt": "继续写作",
                    "max_tokens": 500
                },
                "generate_text"
            )
        
        with ThreadPoolExecutor(max_workers=num_users) as executor:
            futures = [executor.submit(send_generate_request, i) for i in range(num_users * requests_per_user)]
            for future in as_completed(futures):
                scenario_results.append(future.result())
        
        self._print_scenario_results("场景 A", scenario_results)
        return scenario_results

    def run_scenario_b(self, num_requests=100):
        """场景 B：数据库大量数据查询."""
        print(f"\n{'='*60}")
        print(f"场景 B：数据库大量数据查询")
        print(f"{'='*60}")
        print(f"配置: {num_requests} 请求")
        
        # 获取项目列表
        print("\n获取项目列表...")
        projects_resp = self.make_request("GET", "/api/v1/projects?page=1&page_size=20", name="list_projects")
        
        if not projects_resp["success"]:
            print("❌ 获取项目列表失败，跳过场景 B")
            return []
        
        # 查询章节列表（模拟大量数据查询）
        print(f"\n发送 {num_requests} 个查询请求...")
        scenario_results = []
        
        for i in range(num_requests):
            result = self.make_request("GET", "/api/v1/projects/1/chapters", name="view_chapters")
            scenario_results.append(result)
            
            if (i + 1) % 10 == 0:
                print(f"  进度: {i + 1}/{num_requests}")
        
        self._print_scenario_results("场景 B", scenario_results)
        return scenario_results

    def run_scenario_c(self, num_requests=50):
        """场景 C：API 响应时间测试."""
        print(f"\n{'='*60}")
        print(f"场景 C：API 响应时间测试")
        print(f"{'='*60}")
        print(f"配置: {num_requests} 请求，测试所有主要 API")
        
        endpoints = [
            ("GET", "/api/v1/projects", None, "list_projects"),
            ("GET", "/api/v1/projects/stats", None, "get_project_stats"),
            ("GET", "/api/v1/notifications", None, "list_notifications"),
            ("GET", "/api/v1/projects/1", None, "get_project_detail"),
            ("GET", "/api/v1/projects/1/chapters", None, "view_chapters"),
            ("GET", "/api/v1/projects/1/cards", None, "view_cards"),
        ]
        
        scenario_results = []
        
        for endpoint, method, data, name in endpoints:
            print(f"\n测试 {name}...")
            for i in range(num_requests // len(endpoints)):
                result = self.make_request(method, endpoint, data, name)
                scenario_results.append(result)
        
        self._print_scenario_results("场景 C", scenario_results)
        
        # 检查 P95 是否 < 500ms
        print(f"\n{'='*60}")
        print("P95 响应时间检查（目标：< 500ms）")
        print(f"{'='*60}")
        
        grouped = defaultdict(list)
        for r in scenario_results:
            if r["success"]:
                grouped[r["name"]].append(r["response_time_ms"])
        
        all_passed = True
        for name, times in grouped.items():
            times.sort()
            p95 = times[int(len(times) * 0.95)]
            status = "✅" if p95 < 500 else "❌"
            if p95 >= 500:
                all_passed = False
            print(f"{name:<30} P95={p95:.2f}ms {status}")
        
        if all_passed:
            print("\n✅ 所有接口 P95 响应时间 < 500ms")
        else:
            print("\n❌ 部分接口 P95 响应时间 >= 500ms，需要优化")
        
        return scenario_results

    def _print_scenario_results(self, scenario_name, results):
        """打印场景结果."""
        if not results:
            print(f"\n{scenario_name}：无结果")
            return
        
        total = len(results)
        success = sum(1 for r in results if r["success"])
        failed = total - success
        avg_time = sum(r["response_time_ms"] for r in results) / total
        min_time = min(r["response_time_ms"] for r in results)
        max_time = max(r["response_time_ms"] for r in results)
        
        times = sorted([r["response_time_ms"] for r in results if r["success"]])
        p50 = times[int(len(times) * 0.5)] if times else 0
        p95 = times[int(len(times) * 0.95)] if times else 0
        p99 = times[int(len(times) * 0.99)] if times else 0
        
        print(f"\n{scenario_name} 结果:")
        print(f"  总请求数: {total}")
        print(f"  成功: {success} ({success/total*100:.1f}%)")
        print(f"  失败: {failed} ({failed/total*100:.1f}%)")
        print(f"  响应时间:")
        print(f"    - 平均: {avg_time:.2f}ms")
        print(f"    - 最小: {min_time:.2f}ms")
        print(f"    - 最大: {max_time:.2f}ms")
        print(f"    - P50: {p50:.2f}ms")
        print(f"    - P95: {p95:.2f}ms")
        print(f"    - P99: {p99:.2f}ms")
        
        # 保存结果
        self.results.extend(results)

    def save_results(self):
        """保存结果到 JSON 文件."""
        print(f"\n保存结果到 {self.output_file}...")
        
        summary = {
            "timestamp": datetime.now().isoformat(),
            "base_url": self.base_url,
            "total_requests": len(self.results),
            "successful_requests": sum(1 for r in self.results if r["success"]),
            "failed_requests": sum(1 for r in self.results if not r["success"]),
            "average_response_time_ms": sum(r["response_time_ms"] for r in self.results) / len(self.results) if self.results else 0,
        }
        
        output = {
            "summary": summary,
            "results": self.results,
        }
        
        try:
            with open(self.output_file, 'w', encoding='utf-8') as f:
                json.dump(output, f, indent=2, ensure_ascii=False)
            print(f"✅ 结果已保存: {self.output_file}")
        except Exception as e:
            print(f"❌ 保存结果失败: {e}")


def main():
    """主函数."""
    parser = argparse.ArgumentParser(description="墨灵性能测试 — 简化版（使用 requests）")
    parser.add_argument("--host", default="http://localhost:8000", help="后端服务地址")
    parser.add_argument("--users", type=int, default=10, help="并发用户数（场景 A）")
    parser.add_argument("--requests", type=int, default=100, help="每用户请求数（场景 A）或总请求数（场景 B/C）")
    parser.add_argument("--output", default="performance_report.json", help="输出文件名")
    parser.add_argument("--all", action="store_true", help="运行所有测试场景")
    parser.add_argument("--scenario", choices=["a", "b", "c"], help="运行指定场景")
    args = parser.parse_args()
    
    print("="*60)
    print("墨灵性能测试 — 简化版")
    print("="*60)
    print(f"后端地址: <ADDRESS_REDACTED>
    print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)
    
    test = SimplePerformanceTest(base_url=args.host, output_file=args.output)
    
    # 登录
    if not test.register_and_login():
        print("\n❌ 登录失败，退出")
        sys.exit(1)
    
    # 运行测试
    if args.all or args.scenario == "a":
        test.run_scenario_a(num_users=args.users, requests_per_user=args.requests // args.users)
    
    if args.all or args.scenario == "b":
        test.run_scenario_b(num_requests=args.requests)
    
    if args.all or args.scenario == "c":
        test.run_scenario_c(num_requests=args.requests)
    
    # 保存结果
    if test.results:
        test.save_results()
    
    print("\n" + "="*60)
    print("测试完成")
    print("="*60)
    print(f"结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)


if __name__ == "__main__":
    main()
