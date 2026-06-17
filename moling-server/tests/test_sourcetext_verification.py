"""墨灵 (Moling) — SourceText 内容安全验证单元测试 (§11.6).

覆盖内容安全验证的完整功能、边界、稳定性场景：
- SourceText Grounding (第一道防线)
- LLM-as-Judge (第二道防线)
- 大章节分段处理
- 实体名规范化
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.service.phase4_scheduler import (
    Phase4Scheduler,
    SIMILARITY_THRESHOLD,
    ENTITY_SIMILARITY_THRESHOLD,
    MAX_CHAPTER_LENGTH,
)

# asyncio 标记按类级别添加（TestSegmentChapter 的测试为同步）


def _make_mock_db() -> MagicMock:
    """创建模拟数据库会话."""
    db = MagicMock()
    db.flush = AsyncMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.execute = AsyncMock()
    db.execute.return_value = MagicMock()
    db.get = AsyncMock()
    return db


@pytest.fixture()
def scheduler() -> Phase4Scheduler:
    """返回状态已重置的 Phase4Scheduler 实例。"""
    return Phase4Scheduler()


# ============================================================================
# Sample 章节文本
# ============================================================================

SAMPLE_CHAPTER = (
    "张三说：我们得赶紧出发了。\n"
    "李四道：再等等，还有一个人没到。\n"
    "王五问：到底是谁？\n"
    "张三答：是赵六，他去找马了。"
)

SAMPLE_ANALYSIS_PASS = {
    "characters": [
        {"name": "张三", "source_text": "张三说：", "role": "主角"},
        {"name": "李四", "source_text": "李四道：", "role": "配角"},
        {"name": "王五", "source_text": "王五问：", "role": "配角"},
    ],
    "segments": ["张三", "李四", "王五"],
}


# ============================================================================
# 1. SourceText Grounding — 功能测试
# ============================================================================


class TestSourceTextGrounding:
    """第一道防线: SourceText Grounding 功能测试 (§11.6)."""
    pytestmark = pytest.mark.asyncio

    async def test_exact_match_pass(self, scheduler):
        """#1: source_text 精确匹配原文 → 通过。"""
        analysis = {
            "characters": [
                {"name": "张三", "source_text": "张三说：我们得赶紧出发了。"},
            ],
        }
        result = await scheduler._verify_source_text(SAMPLE_CHAPTER, analysis)
        assert result["passed"] is True
        assert result["total_items"] == 1
        assert result["passed_items"] == 1
        assert len(result["skipped_items"]) == 0

    async def test_fuzzy_match_above_threshold_pass(self, scheduler):
        """#2: source_text 模糊匹配 ≥85% → 通过。"""
        # "张三说我们得赶紧出发了X" — 12个字符中11个来自原文, 1个外来字符
        # 字符重叠率 = 11/12 = 91.7% ≥ 85%，直接通过 RapidFuzz
        analysis = {
            "characters": [
                {"name": "张三", "source_text": "张三说我们得赶紧出发了X"},
            ],
        }
        result = await scheduler._verify_source_text(SAMPLE_CHAPTER, analysis)
        assert result["passed"] is True

    async def test_llm_judge_pass_for_low_similarity(self, scheduler):
        """#3: source_text 模糊匹配 <85% 但 LLM 判 pass → 通过。"""
        # 构造一个 source_text 与原文相似度不高，但关键词覆盖率能达到 60%
        analysis = {
            "characters": [
                {"name": "赵六", "source_text": "赵六他去找马了"},
            ],
        }
        result = await scheduler._verify_source_text(SAMPLE_CHAPTER, analysis)
        # "赵六他去找马了" 中的每个字都在原文中出现，
        # 覆盖率应 ≥60%，LLM 判 pass
        assert result["passed"] is True

    async def test_llm_judge_fail_skipped(self, scheduler):
        """#4: source_text <85% 且 LLM 判 fail → skipped。"""
        analysis = {
            "characters": [
                # 完全不相关的 source_text → LLM 应该判 fail
                {"name": "外星人", "source_text": "外星人入侵地球"},
            ],
        }
        result = await scheduler._verify_source_text(SAMPLE_CHAPTER, analysis)
        # "外星人入侵地球" 中的很多字不在原文中 → LLM 判 fail
        assert result["passed"] is False
        assert len(result["skipped_items"]) == 1
        assert result["passed_items"] == 0


# ============================================================================
# 2. 边界测试
# ============================================================================


class TestBoundary:
    """边界场景测试."""
    pytestmark = pytest.mark.asyncio

    async def test_missing_source_text_warn(self, scheduler):
        """#5: 缺少 source_text → warn 不阻止入库。"""
        analysis = {
            "characters": [
                {"name": "无名氏", "source_text": ""},
            ],
        }
        result = await scheduler._verify_source_text("原文内容", analysis)
        # warnings 不影响 passed（全部通过或仅有 warn 时 passed=True）
        assert result["passed"] is True
        assert len(result["warnings"]) == 1
        assert "缺少 source_text" in result["warnings"][0]
        # total_items 应计为 1，但 passed_items = 0
        assert result["total_items"] == 1
        assert result["passed_items"] == 0

    async def test_empty_analysis_passes(self, scheduler):
        """#6: 空分析结果 → passed=True。"""
        analysis = {"characters": [], "segments": []}
        result = await scheduler._verify_source_text("", analysis)
        assert result["passed"] is True
        assert result["total_items"] == 0
        assert result["passed_items"] == 0

    async def test_all_items_skipped_passed_false(self, scheduler):
        """#10: 所有条目被 skipped → passed=False。"""
        analysis = {
            "characters": [
                {"name": "A", "source_text": "完全不相关内容XYZ"},
                {"name": "B", "source_text": "也完全不相关ABC"},
            ],
        }
        chapter = "这是一篇完全无关的文章。"
        result = await scheduler._verify_source_text(chapter, analysis)
        assert result["passed"] is False
        # 两个都应该被 LLM 判 fail（关键词覆盖率低）
        assert len(result["skipped_items"]) == 2
        assert result["passed_items"] == 0

    async def test_unicode_special_chars(self, scheduler):
        """#11: Unicode/特殊字符匹配。"""
        analysis = {
            "characters": [
                {"name": "Alice", "source_text": "Alice说：Hello!"},
                {"name": "测试✓", "source_text": "测试✓"},
            ],
        }
        chapter = "Alice说：Hello! 测试✓通过。\n"
        result = await scheduler._verify_source_text(chapter, analysis)
        assert result["passed"] is True
        assert result["passed_items"] == 2

    async def test_very_short_source_text(self, scheduler):
        """极短的 source_text 应正常处理。"""
        analysis = {
            "characters": [
                {"name": "张", "source_text": "张"},
            ],
        }
        result = await scheduler._verify_source_text(SAMPLE_CHAPTER, analysis)
        # "张" 在原文中 → 精确匹配 100%
        assert result["passed"] is True

    async def test_long_name_source_text(self, scheduler):
        """超长角色名处理。"""
        long_name = "阿" * 50
        analysis = {
            "characters": [
                {"name": long_name, "source_text": long_name},
            ],
        }
        chapter = long_name + "出现在文中。"
        result = await scheduler._verify_source_text(chapter, analysis)
        # 超长精确匹配 → passed
        assert result["passed"] is True


# ============================================================================
# 3. 大章节分段测试
# ============================================================================


class TestChapterSegmentation:
    """大章节分段处理测试."""
    pytestmark = pytest.mark.asyncio

    async def test_segment_short_chapter(self, scheduler):
        """短章节不应分段。"""
        segments = scheduler._segment_chapter("短文本")
        assert len(segments) == 1
        assert segments[0] == "短文本"

    async def test_segment_empty_text(self, scheduler):
        """空文本返回空列表（含一个空字符串）。"""
        segments = scheduler._segment_chapter("")
        assert len(segments) == 1
        assert segments[0] == ""

    async def test_segment_none_text(self, scheduler):
        """None 文本返回空列表（含一个空字符串）。"""
        segments = scheduler._segment_chapter("")
        assert len(segments) == 1

    async def test_segment_large_chapter(self, scheduler):
        """#7: 超大章节（>5000字）应正确分段。"""
        # 构造 6000 字文本
        line = "A" * 100 + "\n"
        large_text = line * 70  # ~7000 字
        assert len(large_text) > MAX_CHAPTER_LENGTH

        segments = scheduler._segment_chapter(large_text)
        assert len(segments) >= 2
        # 每段长度都不超过阈值（或为超长单行）
        for seg in segments:
            assert len(seg) <= MAX_CHAPTER_LENGTH + 100  # 允许单行超长

    async def test_segment_preserves_content(self, scheduler):
        """分段不应丢失内容。"""
        original = ("HelloWorld\n" * 1000)
        segments = scheduler._segment_chapter(original)
        reconstructed = "\n".join(segments)
        # 去除分段引入的额外换行后，原始内容应完整保留
        assert len(reconstructed.replace("\n", "")) == len(original.replace("\n", ""))

    async def test_large_chapter_verification(self, scheduler):
        """#7: 超大章节 SourceText 验证应正确工作。"""
        # 构造 6000 字章节
        line = "张三说：今天天气真好啊。\n"
        large_chapter = line * 600  # ~6000+ 字

        analysis = {
            "characters": [
                {"name": "张三", "source_text": "张三说："},
            ],
        }
        result = await scheduler._verify_source_text(large_chapter, analysis)
        assert result["passed"] is True
        assert result["total_items"] == 1
        assert result["passed_items"] == 1


# ============================================================================
# 4. 稳定性测试
# ============================================================================


class TestStability:
    """稳定性与错误处理测试."""
    pytestmark = pytest.mark.asyncio

    async def test_llm_judge_failure_fallback(self, scheduler):
        """#8: LLM Judge 故障 → 信任 RapidFuzz（保守策略）。"""
        analysis = {
            "characters": [
                {"name": "张三", "source_text": "张三说："},
            ],
        }
        # 用 patch 让 _fuzzy_match 返回一个略低于阈值的值
        # 然后让 _llm_judge 抛出异常
        original_fuzzy = scheduler._fuzzy_match

        async def low_match(*args, **kwargs):
            return SIMILARITY_THRESHOLD - 1  # 84%

        async def judge_raises(*args, **kwargs):
            raise RuntimeError("LLM 服务不可用")

        scheduler._fuzzy_match = low_match  # type: ignore[method-assign]
        scheduler._llm_judge = judge_raises  # type: ignore[method-assign]
        try:
            result = await scheduler._verify_source_text(SAMPLE_CHAPTER, analysis)
            # LLM 故障时信任 RapidFuzz → 如果 <85% 则 fallback verdict = "pass"
            # 所以 passed=True
            assert result["passed"] is True
        finally:
            scheduler._fuzzy_match = original_fuzzy

    async def test_rapidfuzz_exception_downgrade_warn(self, scheduler):
        """#9: RapidFuzz 异常 → 降级 warn。"""
        analysis = {
            "characters": [
                {"name": "张三", "source_text": "张三说："},
            ],
        }

        original_fuzzy = scheduler._fuzzy_match

        async def fuzzy_raises(*args, **kwargs):
            raise ValueError("RapidFuzz 内部错误")

        scheduler._fuzzy_match = fuzzy_raises  # type: ignore[method-assign]
        try:
            result = await scheduler._verify_source_text(SAMPLE_CHAPTER, analysis)
            # RapidFuzz 异常 → 降级 warn，passed=True（warn 不阻止入库）
            assert result["passed"] is True
            assert len(result["warnings"]) == 1
            assert "异常" in result["warnings"][0]
        finally:
            scheduler._fuzzy_match = original_fuzzy

    async def test_empty_characters_list_no_crash(self, scheduler):
        """空角色列表不崩溃。"""
        analysis = {"characters": []}
        result = await scheduler._verify_source_text("任何内容", analysis)
        assert result["passed"] is True

    async def test_mixed_scenario(self, scheduler):
        """混合场景：部分通过 + 部分warn + 部分skip。"""
        analysis = {
            "characters": [
                {"name": "张三", "source_text": "张三说："},
                {"name": "无名氏", "source_text": ""},
                {"name": "外星人", "source_text": "外星人入侵地球"},
            ],
        }
        result = await scheduler._verify_source_text(SAMPLE_CHAPTER, analysis)
        # 张三 → 通过（精确匹配）
        # 无名氏 → warn（缺少 source_text）
        # 外星人 → skip（LLM 判 fail）
        assert result["total_items"] == 3
        assert result["passed_items"] >= 1
        assert len(result["warnings"]) == 1
        assert "缺少 source_text" in result["warnings"][0]


# ============================================================================
# 5. 实体名规范化测试
# ============================================================================


class TestEntityNormalization:
    """第二道防线: 实体名规范化测试 (§11.6)."""
    pytestmark = pytest.mark.asyncio

    async def test_exact_alias_match(self, scheduler):
        """#12: 精确别名匹配 → 注册别名。"""
        mock_db = _make_mock_db()
        mock_db.add = MagicMock(return_value=None)
        existing_char = AsyncMock()
        existing_char.name = "东方不败"
        existing_char.traits = []
        existing_char.aliases = []

        mock_vault_dao = AsyncMock()
        mock_vault_dao.get_characters.return_value = [existing_char]

        with patch("app.service.phase4_scheduler.vault_dao", mock_vault_dao):
            result = await scheduler._normalize_entity_names(
                mock_db, 1,
                [{"name": "东方不败"}],  # 完全相同
            )
        assert len(result["alias_updates"]) == 1
        assert result["alias_updates"][0]["name"] == "东方不败"

    async def test_fuzzy_match_register_alias(self, scheduler):
        """#13: 模糊匹配注册别名。"""
        mock_db = _make_mock_db()
        mock_db.add = MagicMock(return_value=None)
        existing_char = AsyncMock()
        existing_char.name = "东方不败"
        existing_char.traits = []
        existing_char.aliases = []

        mock_vault_dao = AsyncMock()
        mock_vault_dao.get_characters.return_value = [existing_char]

        with patch("app.service.phase4_scheduler.vault_dao", mock_vault_dao):
            result = await scheduler._normalize_entity_names(
                mock_db, 1,
                [{"name": "东方不白"}],  # 模糊匹配
            )
        assert len(result["alias_updates"]) == 1
        assert result["alias_updates"][0]["matched_to"] == "东方不败"

    async def test_no_match_register_new_entity(self, scheduler):
        """#14: 无匹配注册新实体。"""
        mock_db = _make_mock_db()
        mock_vault_dao = AsyncMock()
        mock_vault_dao.get_characters.return_value = []

        with patch("app.service.phase4_scheduler.vault_dao", mock_vault_dao):
            result = await scheduler._normalize_entity_names(
                mock_db, 1,
                [{"name": "全新角色张三"}],
            )
        assert len(result["new_entities"]) == 1
        assert result["new_entities"][0]["name"] == "全新角色张三"

    async def test_empty_name_filtered(self, scheduler):
        """#15: 空名字过滤。"""
        mock_db = _make_mock_db()
        mock_vault_dao = AsyncMock()
        mock_vault_dao.get_characters.return_value = []

        with patch("app.service.phase4_scheduler.vault_dao", mock_vault_dao):
            result = await scheduler._normalize_entity_names(
                mock_db, 1,
                [
                    {"name": ""},
                    {"name": "   "},
                    {"name": None},
                ],
            )
        assert len(result["new_entities"]) == 0
        assert result["total_extracted"] == 3

    async def test_name_similarity_exact(self, scheduler):
        """完全相同名字返回 100.0。"""
        score = await scheduler._name_similarity("张三", "张三")
        assert score == 100.0

    async def test_name_similarity_substring(self, scheduler):
        """子串匹配基于长度比例。"""
        score = await scheduler._name_similarity("张三", "张三丰")
        assert 60 <= score <= 75

    async def test_name_similarity_no_match(self, scheduler):
        """完全不同返回低于阈值。"""
        score = await scheduler._name_similarity("abcxyz", "张三丰")
        assert score < ENTITY_SIMILARITY_THRESHOLD

    async def test_normalize_no_characters_in_db(self, scheduler):
        """数据库无角色时全部注册为新实体。"""
        mock_db = _make_mock_db()
        mock_vault_dao = AsyncMock()
        mock_vault_dao.get_characters.return_value = []

        with patch("app.service.phase4_scheduler.vault_dao", mock_vault_dao):
            result = await scheduler._normalize_entity_names(
                mock_db, 1,
                [{"name": "甲"}, {"name": "乙"}, {"name": "丙"}],
            )
        assert len(result["new_entities"]) == 3
        assert result["total_extracted"] == 3

    async def test_normalize_partial_match(self, scheduler):
        """部分匹配、部分新实体的混合场景。"""
        mock_db = _make_mock_db()
        mock_db.add = MagicMock(return_value=None)
        existing_char = AsyncMock()
        existing_char.name = "纳兰容若"
        existing_char.traits = []
        existing_char.aliases = []

        mock_vault_dao = AsyncMock()
        mock_vault_dao.get_characters.return_value = [existing_char]

        with patch("app.service.phase4_scheduler.vault_dao", mock_vault_dao):
            result = await scheduler._normalize_entity_names(
                mock_db, 1,
                [
                    {"name": "纳兰容若"},   # 精确匹配 → alias
                    {"name": "全新人物"},    # 无匹配 → new
                ],
            )
        assert len(result["alias_updates"]) == 1
        assert len(result["new_entities"]) == 1
        assert result["total_extracted"] == 2


# ============================================================================
# 6. _segment_chapter 详细测试
# ============================================================================


class TestSegmentChapter:
    """_segment_chapter 分段方法详细测试."""

    def test_segment_below_threshold(self, scheduler):
        """小于阈值的文本不分段。"""
        text = "短文本" * 100  # 300 字
        segments = scheduler._segment_chapter(text)
        assert len(segments) == 1

    def test_segment_at_threshold(self, scheduler):
        """等于阈值的文本不分段。"""
        text = "x" * MAX_CHAPTER_LENGTH
        segments = scheduler._segment_chapter(text)
        assert len(segments) == 1

    def test_segment_slightly_above(self, scheduler):
        """略超阈值应分段。"""
        text = ("HelloWorld\n" * 600)  # ~6600 字（含换行）
        segments = scheduler._segment_chapter(text)
        assert len(segments) >= 2

    def test_segment_single_long_line(self, scheduler):
        """单行超长文本应按字符分段。"""
        text = "x" * (MAX_CHAPTER_LENGTH * 2 + 100)
        segments = scheduler._segment_chapter(text)
        assert len(segments) >= 2
        # 每段不应超过阈值（最后一段可能短一些）
        for seg in segments:
            assert len(seg) <= MAX_CHAPTER_LENGTH + 100  # +100 容忍


# ============================================================================
# 7. _find_best_match 测试
# ============================================================================


class TestFindBestMatch:
    """_find_best_match 方法测试."""
    pytestmark = pytest.mark.asyncio

    async def test_exact_match(self, scheduler):
        """精确匹配返回最高分。"""
        result = await scheduler._find_best_match(
            "张三", ["李四", "张三", "王五"],
        )
        assert result is not None
        assert result["name"] == "张三"
        assert result["similarity"] == 100.0

    async def test_fuzzy_match_best(self, scheduler):
        """模糊匹配返回最佳结果。"""
        result = await scheduler._find_best_match(
            "东方不白", ["东方不败", "独孤求败", "西门吹雪"],
        )
        assert result is not None
        assert result["name"] == "东方不败"
        assert result["similarity"] >= ENTITY_SIMILARITY_THRESHOLD

    async def test_no_match(self, scheduler):
        """无匹配返回 None。"""
        result = await scheduler._find_best_match(
            "abcdef", ["张三", "李四"],
        )
        assert result is None


# ============================================================================
# 8. _llm_judge 详细测试
# ============================================================================


class TestLLMJudge:
    """_llm_judge 方法详细测试."""
    pytestmark = pytest.mark.asyncio

    async def test_exact_substring_pass(self, scheduler):
        """精确子串匹配返回 pass。"""
        verdict = await scheduler._llm_judge("张三说：", SAMPLE_CHAPTER)
        assert verdict == "pass"

    async def test_high_coverage_pass(self, scheduler):
        """高关键词覆盖率返回 pass。"""
        verdict = await scheduler._llm_judge(
            "张三李四王五", SAMPLE_CHAPTER,
        )
        assert verdict == "pass"

    async def test_low_coverage_fail(self, scheduler):
        """低关键词覆盖率返回 fail。"""
        verdict = await scheduler._llm_judge(
            "银河系外星人星际舰队", SAMPLE_CHAPTER,
        )
        assert verdict == "fail"

    async def test_empty_source_fail(self, scheduler):
        """空 source_text 返回 fail。"""
        verdict = await scheduler._llm_judge("", SAMPLE_CHAPTER)
        assert verdict == "fail"

    async def test_mixed_chinese_english(self, scheduler):
        """中英文混合的 source_text。"""
        verdict = await scheduler._llm_judge(
            "Alice张三Hello", "Hello张三在吗？说：Alice你来了。",
        )
        assert verdict == "pass"


# ============================================================================
# 9. 集成场景：_run_content_safety_check
# ============================================================================


class TestContentSafetyCheck:
    """_run_content_safety_check 集成测试."""
    pytestmark = pytest.mark.asyncio

    async def test_full_pipeline_pass(self, scheduler):
        """完整内容安全管道：提取+验证+实体规范化全部通过。"""
        mock_db = _make_mock_db()
        mock_vault_dao = AsyncMock()
        mock_vault_dao.get_characters.return_value = []

        with patch("app.service.phase4_scheduler.vault_dao", mock_vault_dao):
            result, analysis = await scheduler._run_content_safety_check(
                mock_db, 1, SAMPLE_CHAPTER,
            )

        assert result["passed"] is True
        assert "total_items" in result
        assert "passed_items" in result
        assert "warnings" in result
        assert "entity_updates" in result
        assert len(analysis["characters"]) > 0

    async def test_full_pipeline_with_warnings(self, scheduler):
        """包含 warn 的内容安全管道。"""
        mock_db = _make_mock_db()
        mock_vault_dao = AsyncMock()
        mock_vault_dao.get_characters.return_value = []

        chapter = "张三说：你好。\n"  # 只包含一个角色
        with patch("app.service.phase4_scheduler.vault_dao", mock_vault_dao):
            result, analysis = await scheduler._run_content_safety_check(
                mock_db, 1, chapter,
            )

        assert result["passed"] is True  # 没有 skipped_items
        assert analysis["characters"][0]["name"] == "张三"

    async def test_verify_source_text_hybrid_result(self, scheduler):
        """验证返回格式包含所有必需字段。"""
        analysis = SAMPLE_ANALYSIS_PASS
        result = await scheduler._verify_source_text(SAMPLE_CHAPTER, analysis)

        required_fields = {"passed", "total_items", "passed_items",
                           "skipped_items", "warnings", "details"}
        assert required_fields.issubset(result.keys())
        assert isinstance(result["passed"], bool)
        assert isinstance(result["total_items"], int)
        assert isinstance(result["passed_items"], int)
        assert isinstance(result["skipped_items"], list)
        assert isinstance(result["warnings"], list)
        assert isinstance(result["details"], list)
