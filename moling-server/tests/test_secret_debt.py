"""墨灵 (Moling) — 秘密债务检查单元测试 (§5.2 第7项 + §2.8.2).

测试 _check_secret_debt() 和 _check_secret_leakage_via_llm() 方法。
所有测试使用 mocking，无需真实数据库。
"""

from __future__ import annotations

import json
from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.service.coherence_service import CoherenceService


# ===== Helpers =====

def _make_mock_secret(
    *,
    secret_id: int = 1,
    description: str = "这是一个测试秘密",
    known_by: list | None = None,
    unknown_to: list | None = None,
    secrecy_level: str = "hidden",
    created_chapter: int = 1,
    debt: int = 0,
) -> MagicMock:
    """创建一个模拟 Secret 对象。"""
    secret = MagicMock()
    secret.id = secret_id
    secret.description = description
    secret.known_by = known_by or ["主角"]
    secret.unknown_to = unknown_to or ["反派"]
    secret.secrecy_level = secrecy_level
    secret.created_chapter = created_chapter
    secret.debt = debt
    return secret


def _make_service() -> CoherenceService:
    """创建一个干净的 CoherenceService 实例。"""
    return CoherenceService()


def _make_mock_db(secrets: list[MagicMock]) -> AsyncMock:
    """创建一个模拟的 AsyncSession，当执行 select(Secret) 时返回给定的秘密列表。"""
    db = AsyncMock()

    # 模拟 db.execute(stmt) 返回一个结果
    async def mock_execute(stmt):
        result = MagicMock()
        scalars_result = MagicMock()
        scalars_result.all.return_value = secrets
        result.scalars.return_value = scalars_result
        return result

    db.execute = mock_execute
    return db


def _make_mock_chapter(chapter_number: int = 5, content: str = "") -> MagicMock:
    """创建一个模拟 Chapter 对象。"""
    chapter = MagicMock()
    chapter.chapter_number = chapter_number
    chapter.id = 100
    chapter.title = f"第{chapter_number}章"
    chapter.content = content
    return chapter


def _make_mock_project(project_id: int = 1) -> MagicMock:
    """创建一个模拟 Project 对象。"""
    project = MagicMock()
    project.id = project_id
    project.title = "测试项目"
    return project


# ===== 测试用例 =====

@pytest.mark.asyncio
async def test_no_secrets():
    """无秘密 → 无告警，passed=True，score=1.0。"""
    service = _make_service()
    db = _make_mock_db(secrets=[])  # 空列表
    project = _make_mock_project()
    chapter = _make_mock_chapter(chapter_number=5)

    result = await service._check_secret_debt(db, project, chapter)

    assert result["passed"] is True
    assert result["score"] == 1.0
    assert result["details"] == []


@pytest.mark.asyncio
async def test_secret_debt_equal_30():
    """债务=30（阈值边界）→ 无告警（阈值 > 30）。"""
    # debt = (5 - 1) * 7 = 4 * 7 = 28 < 30  → 无告警
    secret = _make_mock_secret(
        secret_id=1,
        description="主角的真实身份",
        known_by=["主角"],
        unknown_to=["反派_A", "反派_B", "路人甲", "路人乙", "路人丙", "路人丁", "路人戊"],
        created_chapter=1,
    )
    # unknown_to 有 7 个元素，(5-1)*7 = 28 < 30
    assert len(secret.unknown_to) == 7
    service = _make_service()
    db = _make_mock_db(secrets=[secret])
    project = _make_mock_project()
    chapter = _make_mock_chapter(chapter_number=5)

    result = await service._check_secret_debt(db, project, chapter)

    assert result["passed"] is True
    assert result["score"] == 1.0
    assert result["details"] == []


@pytest.mark.asyncio
async def test_secret_debt_greater_than_30():
    """债务=32（>30）→ 告警。"""
    # debt = (5 - 1) * 8 = 32 > 30
    secret = _make_mock_secret(
        secret_id=1,
        description="宝藏的秘密位置",
        known_by=["主角"],
        unknown_to=[
            "反派_A", "反派_B", "路人甲", "路人乙",
            "路人丙", "路人丁", "路人戊", "路人己",
        ],
        created_chapter=1,
    )
    assert len(secret.unknown_to) == 8
    service = _make_service()
    db = _make_mock_db(secrets=[secret])
    project = _make_mock_project()
    chapter = _make_mock_chapter(chapter_number=5)

    result = await service._check_secret_debt(db, project, chapter)

    assert result["passed"] is True  # 仅有债务告警，非阻塞
    assert result["score"] < 1.0
    assert len(result["details"]) == 1
    d = result["details"][0]
    assert d["debt"] == 32
    assert "建议安排揭露" in d["suggested_fix"]


@pytest.mark.asyncio
async def test_multiple_secrets_high_debt():
    """多秘密 → 高债务告警多次。"""
    secret_a = _make_mock_secret(
        secret_id=1,
        description="魔法石的秘密",
        unknown_to=10 * ["角色"],  # 10人不晓
        created_chapter=1,
    )
    secret_b = _make_mock_secret(
        secret_id=2,
        description="龙族血脉",
        unknown_to=8 * ["角色"],  # 8人不晓
        created_chapter=3,
    )
    # secret_a: (5-1)*10=40 > 30
    # secret_b: (5-3)*8=16 < 30
    service = _make_service()
    db = _make_mock_db(secrets=[secret_a, secret_b])
    project = _make_mock_project()
    chapter = _make_mock_chapter(chapter_number=5)

    result = await service._check_secret_debt(db, project, chapter)

    assert result["passed"] is True
    assert len(result["details"]) == 1  # 只有 secret_a 债务 > 30
    assert result["details"][0]["secret_id"] == 1
    assert result["details"][0]["debt"] == 40


@pytest.mark.asyncio
async def test_secret_revealed():
    """已公开的秘密 (secrecy_level='revealed') → 不参与计算。"""
    secret = _make_mock_secret(
        secret_id=1,
        description="公开的秘密",
        known_by=["所有人"],
        unknown_to=["没人"],
        secrecy_level="revealed",
        created_chapter=1,
    )
    # 即使有 unknow_to，(5-1)*1=4 < 30 但应该被跳过
    service = _make_service()
    db = _make_mock_db(secrets=[secret])
    project = _make_mock_project()
    chapter = _make_mock_chapter(chapter_number=10)

    result = await service._check_secret_debt(db, project, chapter)

    assert result["passed"] is True
    assert result["score"] == 1.0
    assert result["details"] == []


@pytest.mark.asyncio
async def test_secret_open():
    """已公开的秘密 (secrecy_level='open') → 不参与计算。"""
    secret = _make_mock_secret(
        secret_id=1,
        description="公开的秘密",
        known_by=["所有人"],
        unknown_to=["没人"],
        secrecy_level="open",
        created_chapter=1,
    )
    service = _make_service()
    db = _make_mock_db(secrets=[secret])
    project = _make_mock_project()
    chapter = _make_mock_chapter(chapter_number=10)

    result = await service._check_secret_debt(db, project, chapter)

    assert result["passed"] is True
    assert result["score"] == 1.0
    assert result["details"] == []


@pytest.mark.asyncio
async def test_empty_unknown_to():
    """unknown_to 为空 → debt = 0 → 无告警。"""
    secret = _make_mock_secret(
        secret_id=1,
        description="众所周知",
        known_by=["所有人"],
        unknown_to=[],
        created_chapter=1,
    )
    service = _make_service()
    db = _make_mock_db(secrets=[secret])
    project = _make_mock_project()
    chapter = _make_mock_chapter(chapter_number=10)

    result = await service._check_secret_debt(db, project, chapter)

    assert result["passed"] is True
    assert result["score"] == 1.0
    assert result["details"] == []


@pytest.mark.asyncio
async def test_created_chapter_none():
    """created_chapter 为 None → 跳过债务计算。"""
    secret = _make_mock_secret(
        secret_id=1,
        description="无创建时间的秘密",
        known_by=["主角"],
        unknown_to=["反派"],
        created_chapter=None,
    )
    service = _make_service()
    db = _make_mock_db(secrets=[secret])
    project = _make_mock_project()
    chapter = _make_mock_chapter(chapter_number=5)

    result = await service._check_secret_debt(db, project, chapter)

    assert result["passed"] is True
    assert result["score"] == 1.0
    assert result["details"] == []


@pytest.mark.asyncio
async def test_chapter_negative_elapsed():
    """current_chapter < created_chapter → chapters_elapsed 强制为 0。"""
    secret = _make_mock_secret(
        secret_id=1,
        description="未来的秘密",
        known_by=["作者"],
        unknown_to=10 * ["读者"],  # 10人不晓
        created_chapter=8,
    )
    service = _make_service()
    db = _make_mock_db(secrets=[secret])
    project = _make_mock_project()
    chapter = _make_mock_chapter(chapter_number=5)  # 当前 5 < 创建 8

    result = await service._check_secret_debt(db, project, chapter)

    assert result["passed"] is True
    assert result["score"] == 1.0
    assert result["details"] == []


@pytest.mark.asyncio
async def test_llm_failure_graceful_degradation():
    """LLM 调用失败 → 优雅降级（仅返回债务结果）。"""
    secret = _make_mock_secret(
        secret_id=1,
        description="主角身世之谜",
        unknown_to=10 * ["角色"],
        created_chapter=1,
    )
    service = _make_service()

    # patch _check_secret_leakage_via_llm 让它抛异常
    with patch.object(
        service,
        "_check_secret_leakage_via_llm",
        side_effect=RuntimeError("LLM 服务不可用"),
    ):
        db = _make_mock_db(secrets=[secret])
        project = _make_mock_project()
        chapter = _make_mock_chapter(chapter_number=5)

        result = await service._check_secret_debt(db, project, chapter)

    # 虽然 LLM 失败，但债务计算应该正常工作
    assert result["passed"] is True  # 仅有债务建议
    assert len(result["details"]) == 1
    assert result["details"][0]["debt"] == 40


@pytest.mark.asyncio
async def test_llm_conflict_detected():
    """LLM 检测到秘密泄露 → passed=False。"""
    secret = _make_mock_secret(
        secret_id=1,
        description="主角身世之谜",
        known_by=["主角"],
        unknown_to=["反派"],
        created_chapter=1,
    )
    service = _make_service()

    # patch _check_secret_leakage_via_llm 返回冲突
    conflict = {
        "type": "conflict",
        "secret_id": 1,
        "character": "反派",
        "issue": "反派说漏了主角身世",
        "severity": "high",
    }
    with patch.object(
        service,
        "_check_secret_leakage_via_llm",
        return_value=[conflict],
    ):
        db = _make_mock_db(secrets=[secret])
        project = _make_mock_project()
        chapter = _make_mock_chapter(chapter_number=5)

        result = await service._check_secret_debt(db, project, chapter)

    assert result["passed"] is False   # 有冲突标记
    assert result["score"] < 1.0
    assert len(result["details"]) == 1
    assert result["details"][0]["type"] == "conflict"


@pytest.mark.asyncio
async def test_llm_returns_empty_list():
    """LLM 返回空列表 → 无冲突，债务正常计算。"""
    secret = _make_mock_secret(
        secret_id=1,
        description="普通秘密",
        unknown_to=20 * ["角色"],  # 很多人不知
        created_chapter=1,
    )
    service = _make_service()

    with patch.object(
        service,
        "_check_secret_leakage_via_llm",
        return_value=[],
    ):
        db = _make_mock_db(secrets=[secret])
        project = _make_mock_project()
        chapter = _make_mock_chapter(chapter_number=5)

        result = await service._check_secret_debt(db, project, chapter)

    # debt=(5-1)*20=80 > 30 → 债务告警
    assert result["passed"] is True
    assert len(result["details"]) == 1
    assert result["details"][0]["debt"] == 80


@pytest.mark.asyncio
async def test_mixed_debt_and_llm_conflicts():
    """同时存在高债务和 LLM 冲突 → passed=False。"""
    high_debt_secret = _make_mock_secret(
        secret_id=1,
        description="高债务秘密",
        known_by=["主角"],
        unknown_to=10 * ["角色"],
        created_chapter=1,
    )
    # debt=(5-1)*10=40 > 30

    normal_secret = _make_mock_secret(
        secret_id=2,
        description="正常秘密",
        known_by=["主角"],
        unknown_to=["反派"],
        created_chapter=3,
    )
    # debt=(5-3)*1=2 < 30

    service = _make_service()
    conflict = {
        "type": "conflict",
        "secret_id": 2,
        "character": "反派",
        "issue": "反派在对话中暗示了正常秘密",
        "severity": "medium",
    }

    with patch.object(
        service,
        "_check_secret_leakage_via_llm",
        return_value=[conflict],
    ):
        db = _make_mock_db(secrets=[high_debt_secret, normal_secret])
        project = _make_mock_project()
        chapter = _make_mock_chapter(chapter_number=5)

        result = await service._check_secret_debt(db, project, chapter)

    # 有冲突标记 → 不通过
    assert result["passed"] is False
    assert len(result["details"]) >= 2  # 1 个债务 + 1 个冲突
    conflict_details = [d for d in result["details"] if d.get("type") == "conflict"]
    debt_details = [d for d in result["details"] if d.get("debt", 0) > 30]
    assert len(conflict_details) == 1
    assert len(debt_details) == 1


@pytest.mark.asyncio
async def test_llm_leakage_parse_invalid_json():
    """LLM 返回无效 JSON → 优雅处理，不崩溃。"""
    secret = _make_mock_secret(
        secret_id=1,
        description="秘密",
        unknown_to=["反派"],
        created_chapter=1,
    )

    service = _make_service()

    # patch _call_llm 返回无效 JSON
    with patch.object(
        service,
        "_call_llm",
        return_value="这不是 JSON",
    ):
        db = _make_mock_db(secrets=[secret])
        project = _make_mock_project()
        chapter = _make_mock_chapter(chapter_number=5, content="某章节内容")

        # 直接测 _check_secret_leakage_via_llm
        findings = await service._check_secret_leakage_via_llm(
            project, chapter, [secret]
        )

    assert findings == []


@pytest.mark.asyncio
async def test_llm_leakage_returns_non_list():
    """LLM 返回非数组 JSON → 优雅处理。"""
    secret = _make_mock_secret(
        secret_id=1,
        description="秘密",
        unknown_to=["反派"],
        created_chapter=1,
    )

    service = _make_service()

    with patch.object(
        service,
        "_call_llm",
        return_value='{"result": "ok"}',
    ):
        db = _make_mock_db(secrets=[secret])
        project = _make_mock_project()
        chapter = _make_mock_chapter(chapter_number=5, content="内容")

        findings = await service._check_secret_leakage_via_llm(
            project, chapter, [secret]
        )

    assert findings == []


@pytest.mark.asyncio
async def test_llm_leakage_success():
    """LLM 返回有效冲突列表 → 正确解析。"""
    secret = _make_mock_secret(
        secret_id=42,
        description="测试秘密",
        unknown_to=["反派"],
        created_chapter=1,
    )

    service = _make_service()
    llm_response = json.dumps([
        {
            "type": "conflict",
            "secret_id": 42,
            "character": "反派",
            "issue": "反派在对话中透露了测试秘密",
            "severity": "high",
        }
    ])

    with patch.object(
        service,
        "_call_llm",
        return_value=llm_response,
    ):
        project = _make_mock_project()
        chapter = _make_mock_chapter(chapter_number=5, content="内容")

        findings = await service._check_secret_leakage_via_llm(
            project, chapter, [secret]
        )

    assert len(findings) == 1
    assert findings[0]["type"] == "conflict"
    assert "反派" in findings[0]["secret"]
    assert "secret_id" in findings[0] or "秘密#42" in findings[0]["secret"]


@pytest.mark.asyncio
async def test_service_overall_exception_graceful():
    """_check_secret_debt 顶层异常 → 优雅降级。"""
    service = _make_service()
    # 让 db.execute 抛异常
    db = AsyncMock()
    db.execute = MagicMock(side_effect=RuntimeError("DB 连接失败"))
    project = _make_mock_project()
    chapter = _make_mock_chapter(chapter_number=5)

    result = await service._check_secret_debt(db, project, chapter)

    assert result["passed"] is True
    assert result["score"] == 0.8
    assert "error" in result["details"][0]
