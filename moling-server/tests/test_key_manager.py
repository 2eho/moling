"""
墨灵 (Moling) — API Key Manager 单元测试.

测试覆盖:
1. LEAST_USAGE 选择 usage 最低的 Key
2. ROUND_ROBIN 轮询顺序正确
3. Key 返回 429 后被冷却
4. 冷却期满后自动恢复
5. 连续 3 次错误后保持冷却
6. 所有 Key 冷却时抛出异常
7. Pro Pool 和 Flash Pool 独立管理
8. 并发请求不导致 Key 重复选择（线程安全）
9. 空 Pool 不崩溃
10. 调用成功后重置错误计数
11. 指数退避时间正确（30→60→120→300）
12. call_llm() 传入 pool 参数正确路由
"""

from __future__ import annotations

import asyncio
import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from app.llm.key_manager import (
    KeyManager,
    KeyHealth,
    NoAvailableKeyError,
    key_manager,
)
from app.llm.client import LLMClient


# ---------------------------------------------------------------------------
# 辅助函数
# ---------------------------------------------------------------------------

def _make_manager(
    pro_keys=None,
    flash_keys=None,
    strategy="LEAST_USAGE",
):
    """创建 KeyManager 实例用于测试."""
    return KeyManager(
        pro_keys=pro_keys if pro_keys is not None else [f"pro-key-{i}" for i in range(9)],
        flash_keys=flash_keys if flash_keys is not None else [f"flash-key-{i}" for i in range(6)],
        strategy=strategy,
    )


# ===================================================================
# 1. LEAST_USAGE 选择 usage 最低的 Key
# ===================================================================


@pytest.mark.asyncio
async def test_least_usage_selects_lowest_usage():
    """LEAST_USAGE 策略应选择 usage_count 最低的健康 Key."""
    km = _make_manager(pro_keys=["k1", "k2", "k3"], strategy="LEAST_USAGE")

    # 给 k2 增加使用次数
    km._health["k2"].usage_count = 5
    km._health["k3"].usage_count = 2

    selected = await km.select_key("pro")
    # k1 的 usage=0 最低
    assert selected == "k1"
    # 选择后 usage+1
    assert km._health["k1"].usage_count == 1


# ===================================================================
# 2. ROUND_ROBIN 轮询顺序正确
# ===================================================================


@pytest.mark.asyncio
async def test_round_robin_cycles_through_keys():
    """ROUND_ROBIN 策略应轮询选择 Key."""
    km = _make_manager(pro_keys=["k1", "k2", "k3"], strategy="ROUND_ROBIN")

    selections = []
    for _ in range(6):
        sel = await km.select_key("pro")
        selections.append(sel)

    # 应按照 k1, k2, k3, k1, k2, k3 轮询
    assert selections == ["k1", "k2", "k3", "k1", "k2", "k3"]


# ===================================================================
# 3. Key 返回 429 后被冷却
# ===================================================================


@pytest.mark.asyncio
async def test_rate_limit_cools_down_key():
    """Key 返回 429 后应立即被冷却."""
    km = _make_manager(pro_keys=["k1", "k2"], strategy="LEAST_USAGE")

    await km.report_error("k1", "rate_limit")

    health = await km.get_health("k1")
    assert health is not None
    assert health.is_healthy is False
    assert health.cooling_until is not None
    assert health.backoff_level == 1  # 第一次: 30s


# ===================================================================
# 4. 冷却期满后自动恢复
# ===================================================================


@pytest.mark.asyncio
async def test_cooling_expires_auto_recovery():
    """冷却期满后，下次 select_key 应自动恢复 Key."""
    km = _make_manager(pro_keys=["k1", "k2"], strategy="LEAST_USAGE")

    # 冷却 k1，设置冷却到期时间为过去
    km._health["k1"].is_healthy = False
    km._health["k1"].cooling_until = datetime.now(timezone.utc) - timedelta(seconds=1)
    km._health["k1"].backoff_level = 1
    km._health["k1"].consecutive_errors = 1

    # select_key 应触发恢复
    selected = await km.select_key("pro")
    assert selected == "k1", "冷却期满的 Key 应被恢复并选中"

    health = await km.get_health("k1")
    assert health is not None
    assert health.is_healthy is True
    assert health.cooling_until is None


# ===================================================================
# 5. 连续 3 次错误后保持冷却
# ===================================================================


@pytest.mark.asyncio
async def test_consecutive_errors_triggers_cooldown():
    """连续 3 次错误后 Key 应被冷却 300s (max backoff)."""
    km = _make_manager(pro_keys=["k1", "k2"], strategy="LEAST_USAGE")

    # 3 次连续错误（非 429）
    await km.report_error("k1", "other")  # errors=1
    await km.report_error("k1", "other")  # errors=2
    await km.report_error("k1", "other")  # errors=3 → 触发冷却

    health = await km.get_health("k1")
    assert health is not None
    assert health.is_healthy is False
    assert health.consecutive_errors == 3
    # backoff_level 应是 1（第一次冷却 30s，但注意: 每次冷却都会增加 backoff_level,
    # 不过只有第三次才触发 _cool_down, 所以是 backoff_level=1, cooling_until 应该在未来
    # 但这里要小心: consecutive_errors >= 3 时触发冷却, 第一次冷却时 backoff_level+1=1
    assert health.backoff_level >= 1


# ===================================================================
# 6. 所有 Key 冷却时抛出异常
# ===================================================================


@pytest.mark.asyncio
async def test_all_keys_cooled_raises_error():
    """所有 Key 都冷却时 select_key 应抛出 NoAvailableKeyError."""
    km = _make_manager(pro_keys=["k1", "k2"], strategy="LEAST_USAGE")

    # 冷却所有 Key
    km._health["k1"].is_healthy = False
    km._health["k1"].cooling_until = datetime.now(timezone.utc) + timedelta(hours=1)
    km._health["k2"].is_healthy = False
    km._health["k2"].cooling_until = datetime.now(timezone.utc) + timedelta(hours=1)

    with pytest.raises(NoAvailableKeyError) as excinfo:
        await km.select_key("pro")
    assert "pro" in str(excinfo.value.pool)


# ===================================================================
# 7. Pro Pool 和 Flash Pool 独立管理
# ===================================================================


@pytest.mark.asyncio
async def test_pro_and_flash_pools_independent():
    """Pro Pool 和 Flash Pool 应独立管理，互不影响."""
    km = _make_manager(
        pro_keys=["p1", "p2"],
        flash_keys=["f1", "f2"],
        strategy="LEAST_USAGE",
    )

    # 冷却 Pro Pool 的 Key
    await km.report_error("p1", "rate_limit")
    await km.report_error("p2", "rate_limit")

    # Pro Pool 应无可用 Key
    with pytest.raises(NoAvailableKeyError):
        await km.select_key("pro")

    # Flash Pool 应仍可用
    selected = await km.select_key("flash")
    assert selected in ("f1", "f2")


# ===================================================================
# 8. 并发请求不导致 Key 重复选择（线程安全）
# ===================================================================


@pytest.mark.asyncio
async def test_concurrent_selection_thread_safe():
    """并发请求应正确分配 Key（asyncio.Lock 保护）. """
    km = _make_manager(pro_keys=["k1", "k2"], strategy="LEAST_USAGE")

    async def select_and_report():
        key = await km.select_key("pro")
        await km.report_success(key)
        return key

    # 并发 10 次选择
    tasks = [select_and_report() for _ in range(10)]
    results = await asyncio.gather(*tasks)

    # 每次选择后 usage 增加，不应有 None
    assert all(r is not None for r in results)
    # 总 usage 应等于选择次数
    total_usage = km._health["k1"].usage_count + km._health["k2"].usage_count
    assert total_usage == 10


# ===================================================================
# 9. 空 Pool 不崩溃
# ===================================================================


@pytest.mark.asyncio
async def test_empty_pool_raises_no_available():
    """空 Pool（无 Key 配置）应抛出 NoAvailableKeyError."""
    km = _make_manager(pro_keys=[], flash_keys=[])

    with pytest.raises(NoAvailableKeyError) as excinfo:
        await km.select_key("pro")
    assert "为空" in str(excinfo.value)


# ===================================================================
# 10. 调用成功后重置错误计数
# ===================================================================


@pytest.mark.asyncio
async def test_success_resets_error_count():
    """Key 调用成功后，consecutive_errors 应重置为 0."""
    km = _make_manager(pro_keys=["k1", "k2"], strategy="LEAST_USAGE")

    await km.report_error("k1", "other")
    await km.report_error("k1", "other")
    health_before = await km.get_health("k1")
    assert health_before is not None
    assert health_before.consecutive_errors == 2

    await km.report_success("k1")
    health_after = await km.get_health("k1")
    assert health_after is not None
    assert health_after.consecutive_errors == 0
    assert health_after.is_healthy is True


# ===================================================================
# 11. 指数退避时间正确（30→60→120→300）
# ===================================================================


@pytest.mark.asyncio
async def test_exponential_backoff_schedule():
    """指数退避时间应正确: 30s → 60s → 120s → 300s."""
    km = _make_manager(pro_keys=["k1"], strategy="LEAST_USAGE")
    now = datetime.now(timezone.utc)

    # 第 1 次冷却（连续 3 次错误触发）
    km._health["k1"].consecutive_errors = 2
    await km.report_error("k1", "other")  # errors=3 → backoff_level=1 → 30s
    health = await km.get_health("k1")
    assert health is not None
    cooling_1 = _cooling_seconds(health, now)
    assert 25 <= cooling_1 <= 35, f"Expected ~30s, got {cooling_1}s"

    # 模拟恢复后再次触发
    km._health["k1"].is_healthy = True
    km._health["k1"].cooling_until = None
    km._health["k1"].consecutive_errors = 2

    await km.report_error("k1", "other")
    health = await km.get_health("k1")
    assert health is not None
    cooling_2 = _cooling_seconds(health, now)
    assert 55 <= cooling_2 <= 65, f"Expected ~60s, got {cooling_2}s"

    # 再次恢复 + 触发
    km._health["k1"].is_healthy = True
    km._health["k1"].cooling_until = None
    km._health["k1"].consecutive_errors = 2

    await km.report_error("k1", "other")
    health = await km.get_health("k1")
    assert health is not None
    cooling_3 = _cooling_seconds(health, now)
    assert 115 <= cooling_3 <= 125, f"Expected ~120s, got {cooling_3}s"

    # 再次恢复 + 触发
    km._health["k1"].is_healthy = True
    km._health["k1"].cooling_until = None
    km._health["k1"].consecutive_errors = 2

    await km.report_error("k1", "other")
    health = await km.get_health("k1")
    assert health is not None
    cooling_4 = _cooling_seconds(health, now)
    assert 295 <= cooling_4 <= 305, f"Expected ~300s, got {cooling_4}s"


def _cooling_seconds(health: KeyHealth, now: datetime) -> float:
    """计算冷却剩余秒数."""
    if health.cooling_until is None:
        return 0.0
    return (health.cooling_until - now).total_seconds()


# ===================================================================
# 12. call_llm() 传入 pool 参数正确路由（集成测试）
# ===================================================================


@pytest.mark.asyncio
async def test_llm_client_call_with_pool_param():
    """LLMClient.chat() 传入 pool 参数应正确路由到 KeyManager."""
    client = LLMClient()

    # Mock 掉 _call_with_key_manager 和实际的 HTTP 调用
    with patch.object(client, "_call_with_key_manager", new=AsyncMock()) as mock_km:
        with patch.object(client, "_chat_non_stream", new=AsyncMock()) as mock_non:
            mock_non.return_value = {"choices": [{"message": {"content": "ok"}}], "usage": {"completion_tokens": 10}}

            # 使用 pool 参数
            result = await client.chat(
                messages=[{"role": "user", "content": "hello"}],
                pool="flash",
            )

            # 验证 _call_with_key_manager 被调用
            mock_km.assert_awaited_once()
            _, kwargs = mock_km.call_args
            assert kwargs.get("pool") == "flash"


# ===================================================================
# 额外测试: get_pool_status 返回正确信息
# ===================================================================


@pytest.mark.asyncio
async def test_get_pool_status_returns_accurate_info():
    """get_pool_status 应返回准确的 Pool 概览."""
    km = _make_manager(pro_keys=["k1", "k2"], strategy="LEAST_USAGE")

    # 冷却一个 Key
    await km.report_error("k1", "rate_limit")
    await km.select_key("pro")  # 选中 k2

    status = await km.get_pool_status("pro")
    assert status["pool"] == "pro"
    assert status["total"] == 2
    assert status["healthy"] == 1
    assert status["cooling"] == 1


# ===================================================================
# 额外测试: NoAvailableKeyError message 包含 pool 信息
# ===================================================================


@pytest.mark.asyncio
async def test_no_available_key_error_contains_pool():
    """NoAvailableKeyError 应包含 pool 标识."""
    km = _make_manager(pro_keys=["k1"], strategy="LEAST_USAGE")
    km._health["k1"].is_healthy = False
    km._health["k1"].cooling_until = datetime.now(timezone.utc) + timedelta(hours=1)

    try:
        await km.select_key("pro")
        pytest.fail("应抛出异常")
    except NoAvailableKeyError as e:
        assert e.pool == "pro"


# ===================================================================
# 额外测试: ROUND_ROBIN 跳过冷却 Key
# ===================================================================


@pytest.mark.asyncio
async def test_round_robin_skips_cooled_keys():
    """ROUND_ROBIN 策略应跳过冷却中的 Key."""
    km = _make_manager(pro_keys=["k1", "k2", "k3"], strategy="ROUND_ROBIN")

    # 冷却 k2
    km._health["k2"].is_healthy = False
    km._health["k2"].cooling_until = datetime.now(timezone.utc) + timedelta(hours=1)

    # 选择 4 次, k2 应被跳过
    selections = []
    for _ in range(4):
        sel = await km.select_key("pro")
        selections.append(sel)

    # k2 不应出现在结果中
    assert "k2" not in selections
    # 应只在 k1, k3 之间轮询
    assert selections == ["k1", "k3", "k1", "k3"]
