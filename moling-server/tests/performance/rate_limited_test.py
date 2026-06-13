"""墨灵 (Moling) — 考虑速率限制的性能测试.

由于后端启用了速率限制（100请求/60秒），此脚本在请求间添加延迟以符合要求。
"""

from __future__ import annotations

import argparse
import json
import logging
import random
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional

import requests

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)

logger = logging.getLogger(__name__)


@dataclass
class RequestResult:
    endpoint: str
    method: str
    status_code: int
    response_time: float
    success: bool
    error: Optional[str] = None


@dataclass
class TestResults:
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    rate_limited: int = 0  #  429 响应
    server_errors: int = 0  #  500 响应
    results: List[RequestResult] = field(default_factory=list)

    min_response_time: float = 0.0
    max_response_time: float = 0.0
    avg_response_time: float = 0.0
    p50_response_time: float = 0.0
    p95_response_time: float = 0.0

    def calculate_stats(self):
        if not self.results:
            return
        response_times = [r.response_time for r in self.results]
        self.total_requests = len(self.results)
        self.successful_requests = sum(1 for r in self.results if r.success)
        self.failed_requests = self.total_requests - self.successful_requests
        self.rate_limited = sum(1 for r in self.results if r.status_code == 429)
        self.server_errors = sum(1 for r in self.results if r.status_code >= 500)

        if response_times:
            self.min_response_time = min(response_times)
            self.max_response_time = max(response_times)
            self.avg_response_time = sum(response_times) / len(response_times)
            sorted_times = sorted(response_times)
            self.p50_response_time = sorted_times[len(sorted_times) // 2]
            self.p95_response_time = sorted_times[int(len(sorted_times) * 0.95)]


def send_request(session, base_url, method, endpoint, token):
    start_time = time.time()
    try:
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        if method == "GET":
            resp = session.get(f"{base_url}{endpoint}", headers=headers, timeout=10)
        elif method == "POST":
            data = {"email": "test@moling.com", "password": "password123"}
            resp = session.post(f"{base_url}{endpoint}", json=data, headers=headers, timeout=10)
        else:
            resp = session.get(f"{base_url}{endpoint}", headers=headers, timeout=10)

        elapsed = (time.time() - start_time) * 1000
        success = 200 <= resp.status_code < 400
        return RequestResult(
            endpoint=endpoint, method=method,
            status_code=resp.status_code, response_time=elapsed,
            success=success
        )
    except Exception as e:
        elapsed = (time.time() - start_time) * 1000
        return RequestResult(
            endpoint=endpoint, method=method,
            status_code=0, response_time=elapsed,
            success=False, error=str(e)
        )


def worker(worker_id, base_url, num_requests, token, delay):
    session = requests.Session()
    results = []
    for i in range(num_requests):
        #  轮流测试不同端点
        if i % 3 == 0:
            method, endpoint = "GET", "/docs"
            need_auth = False
        elif i % 3 == 1:
            method, endpoint = "GET", "/api/v1/projects"
            need_auth = True
        else:
            method, endpoint = "POST", "/api/v1/auth/login"
            need_auth = False

        result = send_request(
            session, base_url, method, endpoint,
            token if need_auth else None
        )
        results.append(result)
        time.sleep(delay)  #  延迟以避免速率限制
    return results


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="http://localhost:8000")
    parser.add_argument("--users", type=int, default=3)
    parser.add_argument("--requests", type=int, default=20)
    parser.add_argument("--delay", type=float, default=0.7, help="请求间延迟(秒)")
    parser.add_argument("--token", default="test")
    parser.add_argument("--output", default="rate_limited_report.json")
    args = parser.parse_args()

    logger.info(f"开始性能测试(考虑速率限制): {args.host}")
    logger.info(f"用户数: {args.users}, 每用户请求: {args.requests}, 延迟: {args.delay}s")

    all_results = []
    start_time = time.time()

    import concurrent.futures
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.users) as executor:
        futures = [
            executor.submit(worker, i+1, args.host, args.requests, args.token, args.delay)
            for i in range(args.users)
        ]
        for future in concurrent.futures.as_completed(futures):
            all_results.extend(future.result())

    total_time = time.time() - start_time
    results = TestResults(results=all_results)
    results.calculate_stats()
    results.total_time = total_time
    results.throughput = results.total_requests / total_time if total_time > 0 else 0

    #  打印报告
    print("\n" + "=" * 60)
    print("墨灵性能测试报告 (考虑速率限制)")
    print("=" * 60)
    print(f"目标主机: {args.host}")
    print(f"并发用户: {args.users}")
    print(f"每用户请求: {args.requests}")
    print(f"请求间延迟: {args.delay}s")
    print(f"\n总请求数: {results.total_requests}")
    print(f"成功请求: {results.successful_requests}")
    print(f"失败请求: {results.failed_requests}")
    print(f"速率限制(429): {results.rate_limited}")
    print(f"服务器错误(5xx): {results.server_errors}")
    if results.total_requests > 0:
        print(f"成功率: {results.successful_requests / results.total_requests * 100:.1f}%")
    print(f"总耗时: {total_time:.1f}s")
    print(f"吞吐量: {results.throughput:.1f} 请求/秒")

    print(f"\n响应时间统计 (ms):")
    print(f"  最小: {results.min_response_time:.1f}")
    print(f"  最大: {results.max_response_time:.1f}")
    print(f"  平均: {results.avg_response_time:.1f}")
    print(f"  P50: {results.p50_response_time:.1f}")
    print(f"  P95: {results.p95_response_time:.1f}")

    #  性能评估
    print(f"\n--- 性能评估 ---")
    if results.p95_response_time < 500:
        print("[PASS] P95 响应时间 < 500ms (达标)")
    else:
        print("[FAIL] P95 响应时间 >= 500ms (不达标)")

    if results.rate_limited > 0:
        print(f"[WARN]  触发速率限制 {results.rate_limited} 次")
        print(f"   建议：性能测试时提高速率限制阈值")

    print("=" * 60)

    #  保存结果
    output_data = {
        "config": {
            "host": args.host,
            "users": args.users,
            "requests_per_user": args.requests,
            "delay_between_requests": args.delay,
        },
        "summary": {
            "total_requests": results.total_requests,
            "successful_requests": results.successful_requests,
            "failed_requests": results.failed_requests,
            "rate_limited_429": results.rate_limited,
            "server_errors_5xx": results.server_errors,
            "success_rate": results.successful_requests / results.total_requests * 100 if results.total_requests > 0 else 0,
            "total_time": total_time,
            "throughput": results.throughput,
        },
        "response_time_ms": {
            "min": results.min_response_time,
            "max": results.max_response_time,
            "avg": results.avg_response_time,
            "p50": results.p50_response_time,
            "p95": results.p95_response_time,
        },
    }

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)

    logger.info(f"报告已保存到: {args.output}")


if __name__ == "__main__":
    main()
