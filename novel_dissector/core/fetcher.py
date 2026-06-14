"""
= = = = = = = = = = = = = = = = = = = = = = = = = = = = = =
novel_dissector / core / fetcher.py
HTTP 请求模块（带反爬策略）
= = = = = = = = = = = = = = = = = = = = = = = = = = = = = =

移植自写作猫 Go 版 scraper.go 的 HTTPGet 反爬逻辑 + adapter_default.go
的反爬扩展。

核心组件
  - AntiCrawlConfig — 反爬策略配置
  - Fetcher         — 带反爬的 HTTP 客户端
  - FetchResult     — 请求结果

反爬策略
  - 4 组随机 User-Agent 轮换
  - 随机请求延迟（min ~ min+jitter ms）
  - 通用请求头（Accept / Accept-Language / Referer）
  - 超时控制
  - 重试机制（可配置）
  - 硬错误提前终止（不可重试的错误码）
"""

from __future__ import annotations

import random
import time
from dataclasses import dataclass, field
from typing import Optional

try:
    import requests
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry
    _REQUESTS_AVAILABLE = True
except ImportError:
    _REQUESTS_AVAILABLE = False


# ──────────────────────────────────────────────────────── 反爬配置


@dataclass
class AntiCrawlConfig:
    """
    反爬策略配置。
    若 disable_all 为 True，则跳过所有反爬措施（用于内网/测试）。
    """
    user_agents: list[str] = field(default_factory=lambda: _DEFAULT_UAS)
    delay_min_ms: int = 1500
    delay_jitter_ms: int = 2500        # 0~2500ms 额外抖动
    timeout_seconds: int = 30
    max_retries: int = 2
    disable_all: bool = False           # 开发/测试跳过反爬


_DEFAULT_UAS = [
    # Chrome 120 Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    # Chrome 120 macOS
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    # Firefox 119 Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) "
    "Gecko/20100101 Firefox/119.0",
    # Chrome 120 Linux
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
]

# 不可重试的 HTTP 状态码
_HARD_FAILURE_STATUSES = {403, 404, 410, 451, 503}

# 不可重试的连接错误子串
_HARD_FAILURE_PATTERNS = [
    "cloudflare",
    "cf-ray",
    "bad gateway",
    "502 bad gateway",
    "connection reset",
    "connection refused",
]


# ──────────────────────────────────────────────────────── 返回结果


@dataclass
class FetchResult:
    url: str
    status_code: int
    text: str
    headers: dict = field(default_factory=dict)
    elapsed_ms: float = 0.0
    error: Optional[str] = None


# ──────────────────────────────────────────────────────── Fetcher


class Fetcher:
    """
    带反爬策略的 HTTP 请求器。
    对标 Go 版 Scraper.HTTPGet 及 DefaultAdapter.httpGet。
    """

    def __init__(self, config: Optional[AntiCrawlConfig] = None):
        self.config = config or AntiCrawlConfig()
        self._session = self._build_session() if _REQUESTS_AVAILABLE else None
        if not _REQUESTS_AVAILABLE:
            self._warn_missing()

    @staticmethod
    def _warn_missing():
        import warnings
        warnings.warn("requests 库未安装，HTTP 采集功能不可用。请执行: pip install requests")

    def _build_session(self):
        if not _REQUESTS_AVAILABLE:
            return None
        session = requests.Session()
        retry_strategy = Retry(
            total=self.config.max_retries,
            backoff_factor=1.5,
            status_forcelist=[429, 500, 502, 504],
            allowed_methods={"GET", "POST"},
            raise_on_status=False,
        )
        adapter = HTTPAdapter(max_retries=retry_strategy, pool_connections=8, pool_maxsize=16)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        return session

    # ── 公共接口 ──────────────────────────────────────

    def get(self, url: str) -> FetchResult:
        """带反爬的 GET 请求。"""
        if not _REQUESTS_AVAILABLE or self._session is None:
            return FetchResult(url=url, status_code=0, text="", error="requests 库未安装")
        headers = self._make_headers(url)
        if not self.config.disable_all:
            self._random_delay()

        start = time.perf_counter()
        try:
            resp = self._session.get(
                url,
                headers=headers,
                timeout=self.config.timeout_seconds,
                allow_redirects=True,
            )
            elapsed = (time.perf_counter() - start) * 1000

            # 自动检测编码
            if resp.encoding and resp.encoding.upper() in ("GB2312", "GBK", "ISO-8859-1"):
                try:
                    resp.encoding = resp.apparent_encoding or "utf-8"
                except Exception:
                    pass

            return FetchResult(
                url=url,
                status_code=resp.status_code,
                text=resp.text,
                headers=dict(resp.headers),
                elapsed_ms=round(elapsed, 1),
            )
        except requests.RequestException as exc:
            elapsed = (time.perf_counter() - start) * 1000
            error_msg = str(exc).lower()
            if any(p in error_msg for p in _HARD_FAILURE_PATTERNS):
                return FetchResult(
                    url=url, status_code=0, text="",
                    error=f"源站不可用（硬失败）: {exc}",
                    elapsed_ms=round(elapsed, 1),
                )
            return FetchResult(
                url=url, status_code=0, text="",
                error=f"请求失败: {exc}",
                elapsed_ms=round(elapsed, 1),
            )

    def post_form(self, url: str, data: dict[str, str]) -> FetchResult:
        """带反爬的 POST 表单请求（GBK 搜索等场景）。"""
        if not _REQUESTS_AVAILABLE or self._session is None:
            return FetchResult(url=url, status_code=0, text="", error="requests 库未安装")
        headers = self._make_headers(url)
        headers["Content-Type"] = "application/x-www-form-urlencoded"
        if not self.config.disable_all:
            self._random_delay()

        start = time.perf_counter()
        try:
            resp = self._session.post(
                url, data=data, headers=headers,
                timeout=self.config.timeout_seconds, allow_redirects=True,
            )
            elapsed = (time.perf_counter() - start) * 1000
            return FetchResult(
                url=url, status_code=resp.status_code,
                text=resp.text, headers=dict(resp.headers),
                elapsed_ms=round(elapsed, 1),
            )
        except requests.RequestException as exc:
            elapsed = (time.perf_counter() - start) * 1000
            return FetchResult(
                url=url, status_code=0, text="",
                error=f"POST 请求失败: {exc}",
                elapsed_ms=round(elapsed, 1),
            )

    def is_hard_failure(self, result: FetchResult) -> bool:
        """是否硬失败（不应再重试）。"""
        if result.status_code in _HARD_FAILURE_STATUSES:
            return True
        if result.error:
            return any(p in result.error.lower() for p in _HARD_FAILURE_PATTERNS)
        return False

    # ── 内部 ──────────────────────────────────────────

    def _make_headers(self, url: str) -> dict[str, str]:
        if self.config.disable_all:
            return {}
        return {
            "User-Agent": random.choice(self.config.user_agents),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Referer": url,
        }

    def _random_delay(self) -> None:
        delay = self.config.delay_min_ms + random.randint(0, self.config.delay_jitter_ms)
        time.sleep(delay / 1000.0)
