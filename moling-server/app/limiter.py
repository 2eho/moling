"""Shared slowapi Limiter instance — avoids circular imports.

Import from here rather than ``app.main`` so router modules
can decorate endpoints without pulling in the FastAPI app.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

from app.config import get_settings


def _build_default_limits() -> list[str]:
    """从配置构建 slowapi 限流规则."""
    settings = get_settings()
    calls = settings.RATE_LIMIT_CALLS
    period = settings.RATE_LIMIT_PERIOD

    # slowapi 支持的周期单位: second, minute, hour, day
    period_map: dict[int, str] = {
        1: "second",
        60: "minute",
        3600: "hour",
        86400: "day",
    }
    if period in period_map:
        unit = period_map[period]
    else:
        # 非标准周期，使用秒作为单位
        unit = "second"
        calls = int(calls * period)  # 等效换算: calls/period = (calls*period)/second

    return [f"{calls}/{unit}"]


limiter = Limiter(key_func=get_remote_address, default_limits=_build_default_limits())
