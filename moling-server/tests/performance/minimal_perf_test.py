"""墨灵 (Moling) — 极简性能测试脚本.

用于快速验证后端性能，无重试逻辑，超时时间短。

使用方法：
    python minimal_perf_test.py --host http://localhost:8000 --requests 100
"""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import logging
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional

import requests

# ---------------------------------------------------------------------------
# 配置
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)

logger = logging.getLogger(__name__)

#  测试端点列表
TEST_ENDPOINTS = [
    ("GET", "/docs", False),  # 不需要认证
    ("GET", "/api/v1/projects", True),  # 需要认证
    ("POST", "/api/v1/auth/login", False),  # 登录
]


# ---------------------------------------------------------------------------
# 数据类
# ---------------------------------------------------------------------------


@dataclass
class RequestResult:
    """单次请求结果."""

    endpoint: str
    method: str
    status_code: int
    response_time: float  # 毫秒
    success: bool
    error: Optional[str] = None


@dataclass
class TestResults:
    """测试结果统计."""

    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    results: List[RequestResult] = field(default_factory=list)

    #  响应时间统计
    min_response_time: float = 0.0
    max_response_time: float = 0.0
    avg_response_time: float = 0.0
    p50_response_time: float = 0.0
    p95_response_time: float = 0.0

    def calculate_stats(self):
        """计算统计信息."""
        if not self.results:
            return

        response_times = [r.response_time for r in self.results]
        self.total_requests = len(self.results)
        self.successful_requests = sum(1 for r in self.results if r.success)
        self.failed_requests = self.total_requests - self.successful_requests

        if response_times:
            self.min_response_time = min(response_times)
            self.max_response_time = max(response_times)
            self.avg_response_time = sum(response_times) / len(response_times)
            sorted_times = sorted(response_times)
            self.p50_response_time = sorted_times[len(sorted_times) // 2]
            self.p95_response_time = sorted_times[int(len(sorted_times) * 0.95)]


# ---------------------------------------------------------------------------
# 测试函数
# ---------------------------------------------------------------------------


def send_request(session, base_url, method, endpoint, need_auth, token):
    """发送单个请求."""
    start_time = time.time()
    
    try:
        headers = {}
        if need_auth:
            headers["Authorization"] = f"Bearer {token}"
        
        if method == "GET":
            resp = session.get(f"{base_url}{endpoint}", headers=headers, timeout=5)
        elif method == "POST":
            if "login" in endpoint:
                data = {"email": "test@moling.com", "password": "password123"}
            else:
                data = {}
            resp = session.post(f"{base_url}{endpoint}", json=data, headers=headers, timeout=5)
        elif method == "PUT":
            resp = session.put(f"{base_url}{endpoint}", headers=headers, timeout=5)
        elif method == "DELETE":
            resp = session.delete(f"{base_url}{endpoint}", headers=headers, timeout=5)
        else:
            resp = session.get(f"{base_url}{endpoint}", headers=headers, timeout=5)
        
        elapsed = (time.time() - start_time) * 1000
        
        #  判断成功：2xx 或 404（端点不存在但服务器在运行）
        success = 200 <= resp.status_code < 500
        
        return RequestResult(
            endpoint=endpoint,
            method=method,
            status_code=resp.status_code,
            response_time=elapsed,
            success=success,
        )
    except Exception as e:
        elapsed = (time.time() - start_time) * 1000
        return RequestResult(
            endpoint=endpoint,
            method=method,
            status_code=0,
            response_time=elapsed,
            success=False,
            error=str(e),
        )


def worker(worker_id, base_url, num_requests, token):
    """工作线程."""
    session = requests.Session()
    results = []
    
    for i in range(num_requests):
        #  随机选择一个端点
        method, endpoint, need_auth = TEST_ENDPOINTS[i % len(TEST_ENDPOINTS)]
        
        result = send_request(session, base_url, method, endpoint, need_auth, token)
        results.append(result)
        
        if (i + 1) % 10 == 0:
            logger.debug(f"Worker {worker_id}: {i + 1}/{num_requests}")
    
    return results


# ---------------------------------------------------------------------------
# 主函数
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(description="墨灵极简性能测试")
    parser.add_argument("--host", default="http://localhost:8000", help="后端地址")
    parser.add_argument("--users", type=int, default=5, help="并发用户数")
    parser.add_argument("--requests", type=int, default=20, help="每用户请求数")
    parser.add_argument("--token", default="test", help="认证Token")
    parser.add_argument("--output", default="minimal_perf_report.json", help="输出文件")
    
    args = parser.parse_args()
    
    logger.info(f"开始性能测试: {args.host}")
    logger.info(f"用户数: {args.users}, 每用户请求: {args.requests}")
    
    all_results = []
    start_time = time.time()
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.users) as executor:
        futures = []
        for i in range(args.users):
            future = executor.submit(
                worker, i + 1, args.host, args.requests, args.token
            )
            futures.append(future)
        
        for future in concurrent.futures.as_completed(futures):
            results = future.result()
            all_results.extend(results)
    
    total_time = time.time() - start_time
    
    #  统计
    test_results = TestResults(results=all_results)
    test_results.calculate_stats()
    test_results.total_time = total_time
    test_results.throughput = test_results.total_requests / total_time if total_time > 0 else 0
    
    #  打印结果
    print("\n" + "=" * 60)
    print("性能测试结果")
    print("=" * 60)
    print(f"总请求数: {test_results.total_requests}")
    print(f"成功请求数: {test_results.successful_requests}")
    print(f"失败请求数: {test_results.failed_requests}")
    if test_results.total_requests > 0:
        print(f"成功率: {test_results.successful_requests / test_results.total_requests * 100:.1f}%")
    print(f"总耗时: {total_time:.2f}s")
    print(f"吞吐量: {test_results.throughput:.1f} 请求/秒")
    
    print(f"\n响应时间 (ms):")
    print(f"  最小: {test_results.min_response_time:.1f}")
    print(f"  最大: {test_results.max_response_time:.1f}")
    print(f"  平均: {test_results.avg_response_time:.1f}")
    print(f"  P50: {test_results.p50_response_time:.1f}")
    print(f"  P95: {test_results.p95_response_time:.1f}")
    
    #  按端点分组
    print(f"\n按端点统计:")
    endpoint_stats = {}
    for r in all_results:
        key = f"{r.method} {r.endpoint}"
        if key not in endpoint_stats:
            endpoint_stats[key] = {"count": 0, "times": [], "status_codes": []}
        endpoint_stats[key]["count"] += 1
        endpoint_stats[key]["times"].append(r.response_time)
        endpoint_stats[key]["status_codes"].append(r.status_code)
    
    for endpoint, stats in endpoint_stats.items():
        times = stats["times"]
        avg_time = sum(times) / len(times)
        print(f"  {endpoint}: {stats['count']} 请求, 平均 {avg_time:.1f}ms")
    
    print("=" * 60)
    
    #  保存结果
    output_data = {
        "summary": {
            "total_requests": test_results.total_requests,
            "successful_requests": test_results.successful_requests,
            "failed_requests": test_results.failed_requests,
            "total_time": total_time,
            "throughput": test_results.throughput,
        },
        "response_time": {
            "min": test_results.min_response_time,
            "max": test_results.max_response_time,
            "avg": test_results.avg_response_time,
            "p50": test_results.p50_response_time,
            "p95": test_results.p95_response_time,
        },
    }
    
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)
    
    logger.info(f"结果已保存到: {args.output}")


if __name__ == "__main__":
    main()
