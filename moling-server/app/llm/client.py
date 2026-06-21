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
from app.llm.context_budget import ContextBudget
from app.llm.key_manager import KeyManager, key_manager, NoAvailableKeyError

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
# Redis helpers for budget & rate-limit storage (HH10: async Redis)
# ---------------------------------------------------------------------------

def _get_redis_async():
    """Get an async Redis client for budget tracking.

    Uses the same connection parameters as the rest of the app.
    Returns None on failure (graceful degradation to in-process mode).

    The client maintains its own internal connection pool — no manual
    pool management needed.
    """
    try:
        import redis.asyncio as aioredis
        from app.config import get_settings
        s = get_settings()
        return aioredis.Redis(
            host=s.REDIS_HOST or "localhost",
            port=s.REDIS_PORT or 6379,
            db=3,  # DB 3: Token budget / rate-limit counters
            password=s.REDIS_PASSWORD or None,
            decode_responses=True,
            socket_connect_timeout=3,
            socket_timeout=3,
        )
    except Exception:
        return None


def _budget_prefix() -> str:
    """Namespace prefix to avoid key collisions.

    Key format: ``moling:token_budget:{user_id}:{period}:{date_key}``
    """
    return "moling:token_budget"


# ---------------------------------------------------------------------------
# Token Budget Management (HH10: Redis-backed, multi-process safe)
# ---------------------------------------------------------------------------

class TokenBudgetManager:
    """Control token usage budget — Redis-backed for multi-worker safety.

    Falls back gracefully to in-process :class:`defaultdict` storage when
    Redis is unavailable (single-process/dev mode).

    Key format: ``moling:token_budget:{user_id}:{period}:{date_key}``
    where ``user_id`` defaults to ``"global"`` when not provided.

    Configuration:
    - ``TOKEN_BUDGET_LIMIT`` from settings (default 1_000_000 tokens/day)
    - Monthly budget = 30× daily budget
    - Daily keys expire after 2 days; monthly after 45 days
    """

    def __init__(
        self,
        daily_budget: int = 1_000_000,
        monthly_budget: int = 30_000_000,
    ) -> None:
        from app.config import get_settings
        settings = get_settings()
        self.daily_budget = getattr(settings, "TOKEN_BUDGET_LIMIT", daily_budget)
        self.monthly_budget = monthly_budget
        # In-process fallback when Redis is down
        self._daily_usage: Dict[str, int] = defaultdict(int)
        self._monthly_usage: Dict[str, int] = defaultdict(int)
        self._redis = _get_redis_async()
        self._redis_available: Optional[bool] = None  # lazy-checked on first use

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _ensure_redis(self):
        """Check Redis availability once and cache the result.

        Returns the async Redis client, or None if unavailable.
        """
        if self._redis is None:
            self._redis_available = False
            return None
        if self._redis_available is None:
            try:
                import redis.asyncio as _aioredis
                await self._redis.ping()
                self._redis_available = True
            except Exception:
                self._redis_available = False
                logger.warning(
                    "Redis unavailable for token budget, "
                    "falling back to in-process storage"
                )
        return self._redis if self._redis_available else None

    @staticmethod
    def _key(user_id: Optional[str], period: str, date_key: str) -> str:
        """Build Redis key for budget storage.

        Args:
            user_id: User identifier (falls back to ``"global"``).
            period: ``"daily"`` or ``"monthly"``.
            date_key: ``"2026-06-21"`` or ``"2026-06"``.
        """
        uid = user_id or "global"
        return f"{_budget_prefix()}:{uid}:{period}:{date_key}"

    @staticmethod
    def _today_key() -> str:
        return datetime.now(timezone.utc).strftime("%Y-%m-%d")

    @staticmethod
    def _month_key() -> str:
        return datetime.now(timezone.utc).strftime("%Y-%m")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def get_usage(
        self,
        period: str = "daily",
        user_id: Optional[str] = None,
    ) -> int:
        """Get current token usage for a period.

        Args:
            period: ``"daily"`` or ``"monthly"``.
            user_id: Optional user identifier (``None`` → global).

        Returns:
            Token count for the period. Returns 0 on Redis failure
            (graceful degradation — allows requests through).
        """
        date_key = self._today_key() if period == "daily" else self._month_key()

        redis = await self._ensure_redis()
        if redis is not None:
            try:
                key = self._key(user_id, period, date_key)
                val = await redis.get(key)
                return int(val) if val else 0
            except Exception:
                logger.warning(
                    "Redis read failed for token budget (%s), "
                    "using in-process fallback",
                    period,
                )

        # In-process fallback
        if period == "daily":
            return self._daily_usage.get(self._today_key(), 0)
        return self._monthly_usage.get(self._month_key(), 0)

    async def check_budget(
        self,
        estimated_tokens: int,
        user_id: Optional[str] = None,
    ) -> bool:
        """Check if estimated tokens fit within budget.

        Returns True if the request can proceed; False if limits exceeded.
        Redis failures are treated as budget-available (fail-open).
        """
        daily_used = await self.get_usage("daily", user_id)
        monthly_used = await self.get_usage("monthly", user_id)

        if daily_used + estimated_tokens > self.daily_budget:
            logger.warning(
                "Token budget: daily limit exceeded "
                "(%d used / %d budget, +%d estimated)",
                daily_used, self.daily_budget, estimated_tokens,
            )
            return False

        if monthly_used + estimated_tokens > self.monthly_budget:
            logger.warning(
                "Token budget: monthly limit exceeded "
                "(%d used / %d budget, +%d estimated)",
                monthly_used, self.monthly_budget, estimated_tokens,
            )
            return False

        return True

    async def can_use_tokens(
        self,
        estimated_tokens: int,
        user_id: Optional[str] = None,
    ) -> bool:
        """Alias for :meth:`check_budget` (backward compatible)."""
        return await self.check_budget(estimated_tokens, user_id)

    async def record_usage(
        self,
        tokens: int,
        user_id: Optional[str] = None,
    ) -> None:
        """Record token consumption against the budget.

        Uses Redis ``INCR + EXPIRE`` pipeline for atomicity.
        Falls back to in-process counters on Redis failure.
        """
        today = self._today_key()
        this_month = self._month_key()

        redis = await self._ensure_redis()
        if redis is not None:
            try:
                daily_key = self._key(user_id, "daily", today)
                monthly_key = self._key(user_id, "monthly", this_month)
                pipe = redis.pipeline()
                pipe.incrby(daily_key, tokens)
                pipe.expire(daily_key, 86400 * 2)  # 2-day TTL
                pipe.incrby(monthly_key, tokens)
                pipe.expire(monthly_key, 86400 * 45)  # ~1.5-month TTL
                await pipe.execute()
                return
            except Exception:
                logger.warning(
                    "Redis write failed for token budget, "
                    "using in-process fallback"
                )

        # In-process fallback
        self._daily_usage[today] = self._daily_usage.get(today, 0) + tokens
        self._monthly_usage[this_month] = (
            self._monthly_usage.get(this_month, 0) + tokens
        )

    async def get_budget_status(
        self,
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get current budget status for display / admin panel.

        Returns a dict with ``daily``, ``monthly``, and ``backend`` keys.
        ``backend`` is ``"redis"`` (multi-worker safe) or ``"memory"``
        (single-process only).
        """
        daily_used = await self.get_usage("daily", user_id)
        monthly_used = await self.get_usage("monthly", user_id)

        redis = await self._ensure_redis()

        return {
            "daily": {
                "budget": self.daily_budget,
                "used": daily_used,
                "remaining": self.daily_budget - daily_used,
            },
            "monthly": {
                "budget": self.monthly_budget,
                "used": monthly_used,
                "remaining": self.monthly_budget - monthly_used,
            },
            "backend": "redis" if redis is not None else "memory",
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
        # Key Manager（双池管理）
        self.key_manager = key_manager
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
        # Token budget manager (user quotas)
        self.budget_manager = TokenBudgetManager()
        # Context window budget checker (model limits)
        self._context_budget = ContextBudget()

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
        pool: Optional[str] = None,
    ) -> dict[str, Any]:
        """Send a chat completion request (with key pool + fallback).

        Args:
            messages: Chat messages.
            model: Model name (default from config).
            temperature: Sampling temperature.
            max_tokens: Max tokens in response.
            stream: Whether to stream response.
            pool: API Key pool to use ("pro" | "flash").  When set, uses
                  KeyManager for key selection instead of the legacy key pool.

        Returns the full response dict (same format as OpenAI API).
        """
        config = self._get_config()
        model = model or config["model"]

        # Estimate tokens
        estimated_tokens = sum(len(m["content"]) // 4 + 1 for m in messages) + max_tokens

        # Check token budget
        if not await self.budget_manager.can_use_tokens(estimated_tokens):
            raise AppError(
                ErrorCode.RATE_LIMIT_EXCEEDED,
                detail="Token budget exceeded. Please try again later."
            )

        # Check context window budget (L2 fix: integrate ContextBudget)
        prompt_text = json.dumps(messages, ensure_ascii=False)
        ctx_result = self._context_budget.check(
            prompt_text,
            model=model,
            max_output_tokens=max_tokens,
        )
        if not ctx_result.within_budget:
            logger.warning(
                "Context window exceeded: estimated=%d/%d tokens, "
                "overflow=%d tokens. Prompt will be truncated by caller.",
                ctx_result.estimated_input_tokens,
                ctx_result.available_tokens,
                abs(ctx_result.remaining_tokens),
            )
            # 不在此层截断 — 截断由上游 prompt_service 负责
            # 这里只做监测和告警

        # Try with key pool (with fallback)
        last_error = None

        # Use KeyManager when pool is specified
        if pool is not None:
            return await self._call_with_key_manager(
                messages=messages,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=stream,
                pool=pool,
                estimated_tokens=estimated_tokens,
            )

        # Legacy key pool fallback (no pool specified)
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
                    response = await self._chat_stream(payload, api_key)
                    # L1 fix: 流式路径也需要记录 Token 用量 + 上报成功
                    self.key_pool.report_success(api_key)
                    actual_tokens = response.get("usage", {}).get("completion_tokens", 0)
                    self.rate_limiter.record_request(api_key, actual_tokens)
                    await self.budget_manager.record_usage(actual_tokens)
                    return response
                else:
                    response = await self._chat_non_stream(payload, api_key)
                    # Record success
                    self.key_pool.report_success(api_key)
                    actual_tokens = response.get("usage", {}).get("completion_tokens", 0)
                    self.rate_limiter.record_request(api_key, actual_tokens)
                    await self.budget_manager.record_usage(actual_tokens)
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
        api_key: Optional[str] = None,
    ) -> AsyncGenerator[str, None]:
        """Stream a chat completion, yielding content deltas.

        完整的重试 + Key 轮换逻辑：最多重试 3 次，每次从 KeyManager 获取下一个 Key，
        完成后调用 report_success / record_usage / record_request。
        """
        config = self._get_config()
        model = model or config["model"]

        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
        }

        max_retries = 3
        last_error: Optional[Exception] = None

        for attempt in range(max_retries):
            # Get key: prefer provided key on first attempt, then use KeyManager
            if api_key and attempt == 0:
                key = api_key
            else:
                try:
                    key = await self.key_manager.select_key("pro")
                except NoAvailableKeyError:
                    key = self.key_pool.get_key()
                    if not key:
                        raise AppError(
                            ErrorCode.INTERNAL_ERROR,
                            detail="No API key available",
                        )

            collected = ""
            client = self._get_client(key)
            # 为流式响应添加显式 read timeout（防止连接挂起）
            client.timeout = httpx.Timeout(self.timeout, read=30.0)

            try:
                async with client.stream(
                    "POST", "/chat/completions", json=payload
                ) as resp:
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
                                    collected += delta
                                    yield delta
                            except json.JSONDecodeError:
                                continue

                # Stream completed successfully
                await self.key_manager.report_success(key)
                actual_tokens = await self.count_tokens(collected)
                self.rate_limiter.record_request(key, actual_tokens)
                await self.budget_manager.record_usage(actual_tokens)
                return

            except (httpx.TimeoutException, httpx.ConnectError,
                    httpx.RemoteProtocolError, AppError) as e:
                last_error = e
                logger.warning(
                    "chat_stream attempt %d/%d failed: %s",
                    attempt + 1, max_retries, e,
                )
                await self.key_manager.report_error(
                    key,
                    error_type="rate_limit" if "429" in str(e) else "other",
                )
                # If we already yielded content, don't retry (caller received it)
                if collected:
                    logger.error(
                        "Stream partially completed but failed: %d chars yielded",
                        len(collected),
                    )
                    raise

        # All retries exhausted
        raise last_error or AppError(
            ErrorCode.INTERNAL_ERROR, detail="All API keys failed"
        )

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

    async def _call_with_key_manager(
        self,
        messages: list[dict[str, str]],
        model: str,
        temperature: float,
        max_tokens: int,
        stream: bool,
        pool: str,
        estimated_tokens: int,
    ) -> dict[str, Any]:
        """使用 KeyManager 选择 Key 并执行调用.

        支持 Key 健康度检测、冷却和自动恢复.
        """
        last_error: Optional[Exception] = None

        max_attempts = max(len(self.key_manager._get_pool_keys(pool)), 3)
        for attempt in range(max_attempts):
            try:
                api_key = await self.key_manager.select_key(pool)
            except NoAvailableKeyError as e:
                logger.error("Pool %s 无可用 Key: %s", pool, e)
                raise AppError(
                    ErrorCode.INTERNAL_ERROR,
                    detail=f"Pool [{pool}] 无可用 API Key",
                )

            # Check rate limit
            if not self.rate_limiter.can_make_request(api_key, estimated_tokens):
                logger.warning("Rate limit reached for key %s..., switching key...", api_key[:10])
                await self.key_manager.report_error(api_key, "rate_limit")
                last_error = AppError(
                    ErrorCode.RATE_LIMIT_EXCEEDED,
                    detail=f"Rate limit reached for current key, trying next key",
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
                response = await self._chat_non_stream(payload, api_key)
                # Record success
                await self.key_manager.report_success(api_key)
                actual_tokens = response.get("usage", {}).get("completion_tokens", 0)
                self.rate_limiter.record_request(api_key, actual_tokens)
                await self.budget_manager.record_usage(actual_tokens)
                return response

            except AppError as e:
                last_error = e
                if "rate_limit" in str(e).lower() or "429" in str(e):
                    logger.warning("Rate limit error with key %s..., cooling...", api_key[:10])
                    await self.key_manager.report_error(api_key, "rate_limit")
                else:
                    logger.error("LLM request failed with key %s...: %s", api_key[:10], e)
                    await self.key_manager.report_error(api_key, "other")
                continue

        # All attempts failed
        logger.error("Pool %s 所有 Key 均失败", pool)
        raise last_error or AppError(
            ErrorCode.INTERNAL_ERROR,
            detail=f"Pool [{pool}] 所有 API Key 均失败",
        )

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
