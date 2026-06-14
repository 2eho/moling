"""
墨灵 (Moling) — Unified LLM Client.

Supports OpenAI / DeepSeek / compatible API formats with:
- Streaming and non-streaming modes
- Automatic retry via tenacity
- Token counting (approximate)
- Runtime config reload from DB overrides (admin panel)
- API Key Pool + Fallback Chain (§2.7)
- Rate Limit management
- Token budget control
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any, AsyncGenerator, Dict, List, Optional
from datetime import datetime, timezone
from collections import defaultdict

import httpx
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.config import get_effective_llm_config
from app.errors import AppError, ErrorCode

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# API Key Pool Management
# ---------------------------------------------------------------------------

class APIKeyPool:
    """Manage a pool of API keys with fallback chain."""

    def __init__(self, keys: List[str], max_retries: int = 3) -> None:
        self.keys = keys
        self.max_retries = max_retries
        self.current_index = 0
        self.key_errors: Dict[str, int] = defaultdict(int)  # Track errors per key
        self.key_disabled: Dict[str, bool] = defaultdict(bool)  # Track disabled keys

    def get_key(self, index: Optional[int] = None) -> Optional[str]:
        """Get API key by index (with fallback)."""
        if not self.keys:
            return None

        if index is not None:
            return self.keys[index] if index < len(self.keys) else None

        # Return current active key
        attempts = 0
        while attempts < len(self.keys):
            key = self.keys[self.current_index]
            if not self.key_disabled[key]:
                return key
            self._rotate_index()
            attempts += 1

        # All keys disabled, reset and try again
        logger.warning("All API keys disabled, resetting...")
        self.key_disabled.clear()
        for key in self.keys:
            self.key_errors[key] = 0
        return self.keys[0] if self.keys else None

    def report_error(self, key: str, error_type: str = "rate_limit") -> None:
        """Report an error for a key."""
        self.key_errors[key] += 1

        # Disable key if too many errors
        if self.key_errors[key] >= self.max_retries:
            if error_type == "rate_limit":
                # Disable temporarily (will reset after cooldown)
                self.key_disabled[key] = True
                logger.warning(f"API key disabled due to rate limit: {key[:10]}...")
            else:
                # Disable permanently for this session
                self.key_disabled[key] = True
                logger.error(f"API key disabled due to errors: {key[:10]}...")

    def report_success(self, key: str) -> None:
        """Report a success for a key (reset error count)."""
        self.key_errors[key] = 0
        self.key_disabled[key] = False

    def _rotate_index(self) -> None:
        """Rotate to next key index."""
        self.current_index = (self.current_index + 1) % len(self.keys)


# ---------------------------------------------------------------------------
# Rate Limit Management
# ---------------------------------------------------------------------------

class RateLimitTracker:
    """Track rate limits per API key."""

    def __init__(self) -> None:
        self.requests: Dict[str, List[float]] = defaultdict(list)  # key -> list of timestamps
        self.tokens: Dict[str, List[int]] = defaultdict(list)  # key -> list of token counts
        self.max_requests_per_minute = 60  # Configurable
        self.max_tokens_per_minute = 40000  # Configurable

    def can_make_request(self, key: str, estimated_tokens: int = 1000) -> bool:
        """Check if a request can be made within rate limits."""
        now = time.time()
        minute_ago = now - 60

        # Clean old requests
        self.requests[key] = [t for t in self.requests[key] if t > minute_ago]
        self.tokens[key] = [t for t, ts in zip(self.tokens[key], self.requests[key]) if ts > minute_ago]

        # Check request limit
        if len(self.requests[key]) >= self.max_requests_per_minute:
            logger.warning(f"Rate limit: too many requests for key {key[:10]}...")
            return False

        # Check token limit
        total_tokens = sum(self.tokens[key])
        if total_tokens + estimated_tokens > self.max_tokens_per_minute:
            logger.warning(f"Rate limit: token budget exceeded for key {key[:10]}...")
            return False

        return True

    def record_request(self, key: str, token_count: int) -> None:
        """Record a request with token count."""
        now = time.time()
        self.requests[key].append(now)
        self.tokens[key].append(token_count)

    def get_wait_time(self, key: str) -> float:
        """Get recommended wait time before next request (seconds)."""
        if self.can_make_request(key):
            return 0.0

        # Wait until oldest request expires
        if self.requests[key]:
            oldest = min(self.requests[key])
            wait = 60 - (time.time() - oldest)
            return max(wait, 0.1)
        return 0.1


# ---------------------------------------------------------------------------
# Token Budget Management
# ---------------------------------------------------------------------------

class TokenBudgetManager:
    """Control token usage budget."""

    def __init__(self, daily_budget: int = 1000000, monthly_budget: int = 30000000) -> None:
        self.daily_budget = daily_budget
        self.monthly_budget = monthly_budget
        self.daily_usage: Dict[str, int] = defaultdict(int)  # date -> tokens
        self.monthly_usage: Dict[str, int] = defaultdict(int)  # month -> tokens

    def can_use_tokens(self, estimated_tokens: int) -> bool:
        """Check if token budget allows the request."""
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        this_month = datetime.now(timezone.utc).strftime("%Y-%m")

        daily_used = self.daily_usage.get(today, 0)
        monthly_used = self.monthly_usage.get(this_month, 0)

        if daily_used + estimated_tokens > self.daily_budget:
            logger.warning(f"Token budget: daily limit exceeded ({daily_used}/{self.daily_budget})")
            return False

        if monthly_used + estimated_tokens > self.monthly_budget:
            logger.warning(f"Token budget: monthly limit exceeded ({monthly_used}/{self.monthly_budget})")
            return False

        return True

    def record_usage(self, tokens: int) -> None:
        """Record token usage."""
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        this_month = datetime.now(timezone.utc).strftime("%Y-%m")

        self.daily_usage[today] = self.daily_usage.get(today, 0) + tokens
        self.monthly_usage[this_month] = self.monthly_usage.get(this_month, 0) + tokens

    def get_budget_status(self) -> Dict[str, Any]:
        """Get current budget status."""
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        this_month = datetime.now(timezone.utc).strftime("%Y-%m")

        return {
            "daily": {
                "budget": self.daily_budget,
                "used": self.daily_usage.get(today, 0),
                "remaining": self.daily_budget - self.daily_usage.get(today, 0),
            },
            "monthly": {
                "budget": self.monthly_budget,
                "used": self.monthly_usage.get(this_month, 0),
                "remaining": self.monthly_budget - self.monthly_usage.get(this_month, 0),
            },
        }


# ---------------------------------------------------------------------------
# Retry policy for transient failures
# ---------------------------------------------------------------------------

_RETRY_DECORATOR = retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception_type(
        (httpx.TimeoutException, httpx.ConnectError, httpx.RemoteProtocolError)
    ),
    before_sleep=before_sleep_log(logger, 20),
    reraise=True,
)


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------


class LLMClient:
    """Asynchronous LLM client for OpenAI-compatible APIs.

    Reads config at call time from get_effective_llm_config() (DB override > env var).
    This allows admin panel config changes to take effect immediately.

    Features:
    - API Key Pool with fallback chain
    - Rate limit management
    - Token budget control

    Usage::

        client = LLMClient()
        resp = await client.chat(
            messages=[{"role": "user", "content": "Hello"}],
            model="deepseek-chat",
        )
    """

    def __init__(self, timeout: float = 120.0) -> None:
        self.timeout = timeout
        # API Key Pool
        config = get_effective_llm_config()
        api_keys = config.get("api_keys", [])
        if not api_keys:
            # Fallback to single key
            single_key = config.get("api_key", "")
            api_keys = [single_key] if single_key else []
        self.key_pool = APIKeyPool(api_keys)
        # Rate limit tracker
        self.rate_limiter = RateLimitTracker()
        # Token budget manager
        self.budget_manager = TokenBudgetManager()

    def _get_config(self) -> dict[str, Any]:
        """Get current LLM config (DB override > env var)."""
        return get_effective_llm_config()

    def _get_client(self, api_key: str) -> httpx.AsyncClient:
        """Create a new httpx client with current config."""
        config = self._get_config()
        api_base = config["api_base"].rstrip("/")

        return httpx.AsyncClient(
            base_url=api_base,
            timeout=httpx.Timeout(self.timeout),
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def chat(
        self,
        messages: list[dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        stream: bool = False,
    ) -> dict[str, Any]:
        """Send a chat completion request (with key pool + fallback).

        Returns the full response dict (same format as OpenAI API).
        """
        config = self._get_config()
        model = model or config["model"]

        # Estimate tokens
        estimated_tokens = sum(len(m["content"]) // 4 + 1 for m in messages) + max_tokens

        # Check token budget
        if not self.budget_manager.can_use_tokens(estimated_tokens):
            raise AppError(
                ErrorCode.RATE_LIMIT_EXCEEDED,
                detail="Token budget exceeded. Please try again later."
            )

        # Try with key pool (with fallback)
        last_error = None
        for attempt in range(len(self.key_pool.keys)):
            # Get API key
            api_key = self.key_pool.get_key()
            if not api_key:
                raise AppError(
                    ErrorCode.INTERNAL_ERROR,
                    detail="No API key available"
                )

            # Check rate limit
            if not self.rate_limiter.can_make_request(api_key, estimated_tokens):
                logger.warning(f"Rate limit reached for key {api_key[:10]}..., switching key...")
                self.key_pool.report_error(api_key, "rate_limit")
                self.key_pool._rotate_index()
                last_error = AppError(
                    ErrorCode.RATE_LIMIT_EXCEEDED,
                    detail=f"Rate limit reached for current key, trying next key"
                )
                continue

            # Make request
            payload = {
                "model": model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "stream": stream,
            }

            try:
                if stream:
                    return await self._chat_stream(payload, api_key)
                else:
                    response = await self._chat_non_stream(payload, api_key)
                    # Record success
                    self.key_pool.report_success(api_key)
                    actual_tokens = response.get("usage", {}).get("completion_tokens", 0)
                    self.rate_limiter.record_request(api_key, actual_tokens)
                    self.budget_manager.record_usage(actual_tokens)
                    return response

            except AppError as e:
                last_error = e
                if "rate_limit" in str(e).lower() or "429" in str(e):
                    logger.warning(f"Rate limit error with key {api_key[:10]}..., switching to next key...")
                    self.key_pool.report_error(api_key, "rate_limit")
                else:
                    logger.error(f"LLM request failed with key {api_key[:10]}...: {e}")
                    self.key_pool.report_error(api_key, "other")
                # 自动轮换到下一个可用密钥（get_key 内部会跳过已禁用的密钥）
                self.key_pool._rotate_index()
                continue

        # All keys failed
        logger.error("All API keys failed")
        raise last_error or AppError(
            ErrorCode.INTERNAL_ERROR,
            detail="All API keys failed"
        )

    async def chat_stream(
        self,
        messages: list[dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> AsyncGenerator[str, None]:
        """Stream a chat completion, yielding content deltas."""
        config = self._get_config()
        model = model or config["model"]

        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
        }

        # Use first available key
        api_key = self.key_pool.get_key()
        if not api_key:
            raise AppError(
                ErrorCode.INTERNAL_ERROR,
                detail="No API key available"
            )

        client = self._get_client(api_key)
        async with client.stream("POST", "/chat/completions", json=payload) as resp:
            if resp.status_code != 200:
                error_body = await resp.aread()
                raise _build_error(resp.status_code, error_body)

            async for line in resp.aiter_lines():
                if line.startswith("data: "):
                    data_str = line[6:].strip()
                    if data_str == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data_str)
                        delta = (
                            chunk.get("choices", [{}])[0]
                            .get("delta", {})
                            .get("content", "")
                        )
                        if delta:
                            yield delta
                    except json.JSONDecodeError:
                        continue

    async def count_tokens(self, text: str) -> int:
        """Approximate token count (4 chars ≈ 1 token for Chinese/English)."""
        return len(text) // 4 + 1

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @_RETRY_DECORATOR
    async def _chat_non_stream(self, payload: dict, api_key: str) -> dict:
        client = self._get_client(api_key)
        try:
            resp = await client.post("/chat/completions", json=payload)
            if resp.status_code != 200:
                raise _build_error(resp.status_code, resp.content)
            return resp.json()
        finally:
            await client.aclose()

    async def _chat_stream(self, payload: dict, api_key: str) -> dict:
        """Collect a full streamed response into a single dict.

        For streaming consumers, prefer ``chat_stream()``.
        """
        full_content = ""
        async for delta in self.chat_stream(**payload, api_key=api_key):
            full_content += delta

        return {
            "choices": [
                {
                    "message": {"content": full_content, "role": "assistant"},
                    "finish_reason": "stop",
                }
            ],
            "usage": {"completion_tokens": await self.count_tokens(full_content)},
        }

    async def aclose(self) -> None:
        """Close the underlying HTTP client."""
        # No persistent client - nothing to close
        pass


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

llm_client = LLMClient()


# ---------------------------------------------------------------------------
# Error builder
# ---------------------------------------------------------------------------


def _build_error(status_code: int, body: bytes) -> AppError:
    """Build an appropriate exception from an API error response."""
    try:
        detail = json.loads(body).get("error", {}).get("message", str(body))
    except Exception:
        detail = str(body)

    if status_code == 429:
        return AppError(ErrorCode.RATE_LIMIT_EXCEEDED, detail=detail)
    return AppError(ErrorCode.INTERNAL_ERROR, detail=f"LLM 服务错误: {detail}")
