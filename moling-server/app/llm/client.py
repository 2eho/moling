"""
墨灵 (Moling) — Unified LLM Client.

Supports OpenAI / DeepSeek / compatible API formats with:
- Streaming and non-streaming modes
- Automatic retry via tenacity
- Token counting (approximate)
- Runtime config reload from DB overrides (admin panel)
"""

from __future__ import annotations

import json
from typing import Any, AsyncGenerator, Optional

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

# ---------------------------------------------------------------------------
# Retry policy for transient failures
# ---------------------------------------------------------------------------

_RETRY_DECORATOR = retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception_type(
        (httpx.TimeoutException, httpx.ConnectError, httpx.RemoteProtocolError)
    ),
    before_sleep=before_sleep_log(__import__("logging").getLogger(__name__), 20),
    reraise=True,
)


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------


class LLMClient:
    """Asynchronous LLM client for OpenAI-compatible APIs.

    Reads config at call time from get_effective_llm_config() (DB override > env var).
    This allows admin panel config changes to take effect immediately.

    Usage::

        client = LLMClient()
        resp = await client.chat(
            messages=[{"role": "user", "content": "Hello"}],
            model="deepseek-chat",
        )
    """

    def __init__(self, timeout: float = 120.0) -> None:
        self.timeout = timeout
        # Don't create httpx client at init time - create per-request
        # so config changes take effect immediately

    def _get_config(self) -> dict[str, str]:
        """Get current LLM config (DB override > env var)."""
        return get_effective_llm_config()

    def _get_client(self) -> httpx.AsyncClient:
        """Create a new httpx client with current config."""
        config = self._get_config()
        api_base = config["api_base"].rstrip("/")
        api_key = config["api_key"]

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
        """Send a chat completion request.

        Returns the full response dict (same format as OpenAI API).
        """
        config = self._get_config()
        model = model or config["model"]

        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": stream,
        }

        if stream:
            return await self._chat_stream(payload)
        else:
            return await self._chat_non_stream(payload)

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

        client = self._get_client()
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
    async def _chat_non_stream(self, payload: dict) -> dict:
        client = self._get_client()
        try:
            resp = await client.post("/chat/completions", json=payload)
            if resp.status_code != 200:
                raise _build_error(resp.status_code, resp.content)
            return resp.json()
        finally:
            await client.aclose()

    @_RETRY_DECORATOR
    async def _chat_stream(self, payload: dict) -> dict:
        """Collect a full streamed response into a single dict.

        For streaming consumers, prefer ``chat_stream()``.
        """
        full_content = ""
        async for delta in self.chat_stream(**payload):
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
