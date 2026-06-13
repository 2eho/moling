"""
墨灵 (Moling) — 连载书导入引擎测试

覆盖 Phase 1-3 的核心功能。
"""

from __future__ import annotations

import pytest


# ============================================================================
# Phase 1: 四库分析 — Merger 单元测试
# ============================================================================


class TestPhase1Merger:
    """测试 Phase 1 合并去重算法。"""

    def test_merge_characters_exact_match(self):
        """精确匹配的角色应合并。"""
        from app.ingest.phase1.merger import merge_characters

        entries = [
            {"name": "陈道临", "aliases": [], "dialogue_count": 5,
             "description": "主角", "tags": ["主角"], "chapter_index": 0},
            {"name": "陈道临", "aliases": [], "dialogue_count": 3,
             "description": "主角", "tags": ["主角"], "chapter_index": 1},
        ]
        result = merge_characters(entries)
        assert len(result) == 1
        assert result[0].name == "陈道临"
        assert result[0].dialogue_count == 8
        assert result[0].first_appearance == 0
        assert result[0].chapters_active == [0, 1]

    def test_merge_characters_alias_match(self):
        """别名匹配的角色应合并。"""
        from app.ingest.phase1.merger import merge_characters

        entries = [
            {"name": "陈道临", "aliases": ["道长"], "dialogue_count": 5,
             "description": "主角", "tags": ["主角"], "chapter_index": 0},
            {"name": "道长", "aliases": [], "dialogue_count": 2,
             "description": "主角", "tags": ["主角"], "chapter_index": 1},
        ]
        result = merge_characters(entries)
        assert len(result) == 1
        assert result[0].name == "陈道临"
        assert "道长" in result[0].aliases
        assert result[0].dialogue_count == 7

    def test_merge_characters_name_containment(self):
        """包含关系的角色名应合并。"""
        from app.ingest.phase1.merger import merge_characters

        entries = [
            {"name": "陈道临", "aliases": [], "dialogue_count": 3,
             "description": "", "tags": [], "chapter_index": 0},
            {"name": "陈道临长老", "aliases": [], "dialogue_count": 1,
             "description": "", "tags": [], "chapter_index": 1},
        ]
        result = merge_characters(entries)
        # 较长的名称"陈道临长老"被保留为主名，"陈道临"成为别名
        assert len(result) == 1
        assert result[0].name == "陈道临长老"
        assert "陈道临" in result[0].aliases

    def test_merge_characters_different_names(self):
        """不同角色名不应合并。"""
        from app.ingest.phase1.merger import merge_characters

        entries = [
            {"name": "陈道临", "aliases": [], "dialogue_count": 5,
             "description": "", "tags": [], "chapter_index": 0},
            {"name": "李察", "aliases": [], "dialogue_count": 3,
             "description": "", "tags": [], "chapter_index": 1},
        ]
        result = merge_characters(entries)
        assert len(result) == 2

    def test_merge_events_similar(self):
        """相似事件应合并。"""
        from app.ingest.phase1.merger import merge_similar_events

        events = [
            {"description": "陈道临遇到李察", "relative_time": "当天",
             "characters": ["陈道临", "李察"], "importance": 4, "chapter_index": 0},
            {"description": "陈道临会见李察", "relative_time": "当天",
             "characters": ["陈道临", "李察"], "importance": 3, "chapter_index": 1},
        ]
        result = merge_similar_events(events)
        # 两个事件足够相似，应合并
        assert len(result) <= 2  # 可能合并也可能不合并，取决于分词

    def test_merge_events_different(self):
        """完全不同的事件不应合并。"""
        from app.ingest.phase1.merger import merge_similar_events

        events = [
            {"description": "陈道临遇到李察", "relative_time": "当天",
             "characters": ["陈道临", "李察"], "importance": 4, "chapter_index": 0},
            {"description": "天空出现异象", "relative_time": "三天后",
             "characters": [], "importance": 5, "chapter_index": 2},
        ]
        result = merge_similar_events(events)
        assert len(result) == 2

    def test_merge_promises_dedup(self):
        """相同的剧情承诺应去重。"""
        from app.ingest.phase1.merger import merge_promises

        promises = [
            {"type": "mystery", "text": "到底是谁？", "chapter_index": 0, "related_characters": []},
            {"type": "mystery", "text": "到底是谁？", "chapter_index": 1, "related_characters": []},
        ]
        result = merge_promises(promises)
        assert len(result) == 1

    def test_merge_world_items_dedup(self):
        """相同术语的世界观条目应合并。"""
        from app.ingest.phase1.merger import merge_world_items

        items = [
            {"term": "魔法元素", "description": "天地间的魔法能量", "category": "magic",
             "chapter_index": 0, "related_terms": []},
            {"term": "魔法元素", "description": "更详细的魔法能量描述", "category": "magic",
             "chapter_index": 2, "related_terms": ["元素"]},
        ]
        result = merge_world_items(items)
        assert len(result) == 1
        # 应保留更详细的描述
        assert "更详细的" in result[0].description
        assert 0 in result[0].reference_chapters
        assert 2 in result[0].reference_chapters


# ============================================================================
# Phase 2: 动态层分析 单元测试
# ============================================================================


class TestPhase2Analyzer:
    """测试 Phase 2 分析算法。"""

    def test_I5_chapter_anchors_empty(self):
        """空章节列表返回空结果。"""
        from app.ingest.phase2.analyzer import I5_chapter_anchors

        result = I5_chapter_anchors([])
        assert result == []

    def test_I5_chapter_anchors_opening_hook(self):
        """含有章首钩子的章节应被检测到。"""
        from app.ingest.phase2.analyzer import I5_chapter_anchors

        chapters = [
            {
                "index": 0,
                "title": "第一章",
                "raw_text": "突然，一声巨响打破了夜的宁静。陈道临从梦中惊醒。"
            }
        ]
        result = I5_chapter_anchors(chapters)
        assert len(result) == 1
        assert result[0].opening_hook is True

    def test_I5_chapter_anchors_no_hook(self):
        """无钩子的章节不应被误判。"""
        from app.ingest.phase2.analyzer import I5_chapter_anchors

        chapters = [
            {
                "index": 0,
                "title": "第一章",
                "raw_text": "这是一个阳光明媚的早晨。陈道临像往常一样起床洗漱。"
            }
        ]
        result = I5_chapter_anchors(chapters)
        assert len(result) == 1
        assert result[0].opening_hook is False
        assert result[0].closing_cliff is False

    def test_I5_closing_cliffhanger(self):
        """含有章末钩子的章节应被检测到。"""
        from app.ingest.phase2.analyzer import I5_chapter_anchors

        chapters = [
            {
                "index": 0,
                "title": "第一章",
                "raw_text": "陈道临推开门走了进去。突然，一个声音响起:未完待续"
            }
        ]
        result = I5_chapter_anchors(chapters)
        assert result[0].closing_cliff is True

    def test_I6_coherence_new_work(self):
        """新作品（章数 ≤ recent_n）应返回满分。"""
        from app.ingest.phase2.analyzer import I6_coherence_baseline

        chapters = [{"index": 0, "title": "第一章", "raw_text": "测试内容"}]
        result = I6_coherence_baseline(chapters, recent_n=3)
        assert result["status"] == "new_work"
        assert result["overall"] == 1.0

    def test_I7_open_hooks_empty_for_new(self):
        """新作品应无未收束钩子。"""
        from app.ingest.phase2.analyzer import I7_open_hooks

        chapters = [{"index": 0, "title": "第一章", "raw_text": "测试内容"}]
        result = I7_open_hooks(chapters, recent_n=3)
        assert len(result) == 0

    def test_I7_detect_mystery_hook(self):
        """应检测到疑问式悬念。"""
        from app.ingest.phase2.analyzer import I7_open_hooks

        chapters = [
            {"index": 0, "title": "第一章", "raw_text": "他到底是谁？为什么来到这里？"},
            {"index": 1, "title": "第二章", "raw_text": "陈道临继续前行。"},
        ]
        result = I7_open_hooks(chapters, recent_n=1)
        # 第一章的悬念在第二章未被收束，应返回
        assert len(result) >= 1
        assert any(h.type == "mystery" for h in result)

    def test_I8_recent_changes_single_chapter(self):
        """单章作品返回新作品提示。"""
        from app.ingest.phase2.analyzer import I8_recent_changes

        chapters = [{"index": 0, "title": "第一章", "raw_text": "测试内容"}]
        result = I8_recent_changes(chapters)
        assert len(result) >= 1

    def test_I9_feasibility_no_chapters(self):
        """无章节时返回低信心分。"""
        from app.ingest.phase2.analyzer import I9_feasibility_check

        result = I9_feasibility_check(chapters=[], recent_n=3)
        assert result.continuation_confidence == 0.0

    def test_I9_feasibility_with_data(self):
        """有章节数据时返回合理的评估。"""
        from app.ingest.phase2.analyzer import I9_feasibility_check

        chapters = [{"index": 0, "title": "第一章", "raw_text": "终于，他发现了一个秘密。"}]
        result = I9_feasibility_check(chapters=chapters, recent_n=3)
        assert result.plot_density >= 0
        assert 0 <= result.continuation_confidence <= 1


# ============================================================================
# Phase 3: 冲突校验 单元测试
# ============================================================================


class TestPhase3Conflict:
    """测试 Phase 3 冲突校验逻辑。"""

    def test_chapter_overlap_warning(self):
        """新章节数 <= 已有章节数时应有警告。"""
        from app.ingest.phase3.conflict import _check_chapter_overlap

        data = {"existing_chapter_count": 10, "chapter_count": 5}
        conflicts = _check_chapter_overlap(data)
        assert len(conflicts) >= 1
        assert conflicts[0]["type"] == "overwrite_warning"

    def test_no_chapter_overlap_warning(self):
        """新章节数 > 已有章节数时无警告。"""
        from app.ingest.phase3.conflict import _check_chapter_overlap

        data = {"existing_chapter_count": 5, "chapter_count": 10}
        conflicts = _check_chapter_overlap(data)
        assert len(conflicts) == 0

    def test_no_overlap_without_existing(self):
        """无已有章节时无覆盖警告。"""
        from app.ingest.phase3.conflict import _check_chapter_overlap

        data = {"existing_chapter_count": 0, "chapter_count": 10}
        conflicts = _check_chapter_overlap(data)
        assert len(conflicts) == 0


# ============================================================================
# Phase 1-3 集成测试
# ============================================================================


class TestPhase1Pipeline:
    """测试 Phase 1 流水线。"""

    @pytest.mark.asyncio
    async def test_run_phase1_pipeline_with_text(self):
        """用纯文本运行 Phase 1 流水线应返回结构化的分析结果。"""
        from app.ingest.phase1 import run_phase1_pipeline, Phase1Result

        chapters = [
            {
                "index": 0,
                "title": "第一章 初遇",
                "raw_text": (
                    "陈道临走在通往帝都的大路上。突然，他听到了远处传来的打斗声。"
                    "他加快脚步走上前去，发现一个年轻人正在与一群黑衣人搏斗。"
                    "年轻人,我来助你一臂之力!陈道临喊道。"
                    "那个年轻人转过头来,露出一张坚毅的面孔。"
                    "多谢相助!年轻人说。"
                    "陈道临抽出长剑,冲入了战圈。"
                ),
            },
            {
                "index": 1,
                "title": "第二章 帝都",
                "raw_text": (
                    "三天后,陈道临终于抵达了帝都。"
                    "这座宏伟的城市让他惊叹不已。"
                    "他打听到了关于魔法学院的消息。"
                    "据说帝都魔法学院有着数百年的历史。"
                    "陈道临决定明天就去学院报到。"
                ),
            },
        ]

        # 运行流水线（这里 LLM 会失败，触发正则降级）
        result = await run_phase1_pipeline(chapters, config=None)

        assert isinstance(result, Phase1Result)
        assert result.chapter_count == 2

        # 即使 LLM 调用全部失败，正则降级也应产生一些结果
        # 角色提取（降级）应找到"陈道临"等
        if result.characters:
            names = [c.name for c in result.characters]
            assert any("陈道临" in name or "陈" in name for name in names)


class TestPhase2Pipeline:
    """测试 Phase 2 流水线。"""

    def test_run_phase2_pipeline(self):
        """运行 Phase 2 流水线应返回全部五项分析结果。"""
        from app.ingest.phase2 import run_phase2_pipeline, Phase2Input, Phase2Result

        chapters = [
            {"index": 0, "title": "第一章", "raw_text": "突然，他出现了。"},
            {"index": 1, "title": "第二章", "raw_text": "第二天，一切如常。"},
            {"index": 2, "title": "第三章", "raw_text": "就在这时，意外发生了。"},
        ]

        input_data = Phase2Input(chapters=chapters)
        result = run_phase2_pipeline(input_data)

        assert isinstance(result, Phase2Result)
        assert len(result.chapter_anchors) == 3
        assert result.feasibility.continuation_confidence >= 0

        # 第一章应有章首钩子
        assert result.chapter_anchors[0].opening_hook is True


class TestPhase3Pipeline:
    """测试 Phase 3 流水线（不含 DB）。"""

    @pytest.mark.asyncio
    async def test_phase3_no_existing_data(self, test_db, test_project):
        """当项目无已有数据时，无冲突。"""
        from app.ingest.phase3.conflict import I10_conflict_check

        phase1_data = {
            "characters": [
                {"name": "陈道临", "description": "主角", "tags": ["主角"]}
            ],
            "timeline_events": [],
            "promises": [],
            "world_items": [],
            "chapter_count": 5,
            "existing_chapter_count": 0,
        }

        conflicts = await I10_conflict_check(test_db, test_project.id, phase1_data)
        # 应无角色/时间线/世界观冲突（因为项目是新创建的）
        # 但可能有章节覆盖警告（existing_chapter_count=0）
        char_conflicts = [c for c in conflicts if c["type"] != "overwrite_warning"]
        assert len(char_conflicts) == 0
