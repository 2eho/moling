"""墨灵 (Moling) — §3.5 Prompt分层组装 单元测试。

覆盖 _build_generation_prompt() 的三层注入结构及各种降级情况。
"""

from typing import Any, Dict, List, Optional

import pytest

from app.models import Chapter, Project

# ============================================================================
# Helpers — 构造测试数据
# ============================================================================


def _make_project(**kwargs) -> Project:
    """Create a minimal Project instance for testing."""
    defaults = dict(
        id=1,
        user_id="test-user",
        title="星穹纪元",
        author="墨灵",
        genre="科幻",
        synopsis="在遥远的未来，人类踏入星际时代...",
        worldview="硬科幻设定，光速不可超越，量子纠缠通讯可用",
        style="写实",
        status="active",
        creation_mode="from_scratch",
    )
    defaults.update(kwargs)
    return Project(**defaults)


def _make_chapter(**kwargs) -> Chapter:
    """Create a minimal Chapter instance for testing."""
    defaults = dict(
        id=1,
        project_id=1,
        title="启程",
        chapter_number=1,
        status="draft",
        phase4_status="pending",
    )
    defaults.update(kwargs)
    return Chapter(**defaults)


def _make_outline(**kwargs) -> Dict[str, Any]:
    """Create a standard outline dict; merge caller overrides."""
    defaults: Dict[str, Any] = {
        "chapter_title": "启程",
        "chapter_number": 1,
        "selected_directions": [
            {
                "card_name": "主角觉醒",
                "direction_text": "主角在危机中觉醒潜能",
                "weight": 0.8,
            },
        ],
        "characters": ["林星", "陈博士"],
        "recent_events": ["主角收到神秘信号", "陈博士失踪"],
        "active_promises": ["神秘信号来源之谜"],
        "generation_requirements": {
            "word_count": "2500-3500",
            "style": "写实",
        },
    }
    defaults.update(kwargs)
    return defaults


def _make_vault(
    with_dynamic_layer: bool = True,
    with_chars: bool = True,
    with_promises: bool = True,
    with_timeline: bool = True,
    with_world: bool = True,
) -> Dict[str, Any]:
    """Build relevant_vault dict with per-section toggle."""
    vault: Dict[str, Any] = {}
    if with_dynamic_layer:
        vault["dynamic_layer"] = {
            "summary": "林星收到一段来自未知文明的加密信号，陈博士在解读过程中神秘失踪。",
            "anchor_pov": "林星",
            "anchor_location": "深空观测站·阿尔法区",
            "anchor_time": "星际历217年·秋",
            "must_hold": ["林星拥有信号解读能力", "陈博士已失踪"],
            "must_not": ["陈博士突然回归", "信号来源立即揭示"],
            "unresolved_hooks": [
                {"description": "神秘信号的真正含义是什么？"},
                {"description": "陈博士去了哪里？"},
                {"description": "观测站内是否有内鬼？"},
            ],
        }
    if with_chars:
        vault["characters"] = [
            {
                "name": "林星",
                "role": "protagonist",
                "description": "年轻的星际语言学家",
                "personality": "好奇心强，执着",
                "current_state": "焦虑不安",
            },
            {
                "name": "陈博士",
                "role": "ally",
                "description": "资深天体物理学家",
                "current_state": "失踪",
            },
        ]
    if with_promises:
        vault["plot_promises"] = [
            {
                "description": "神秘信号来源之谜",
                "status": "active",
                "urgency": 8,
            },
        ]
    if with_timeline:
        vault["timeline"] = [
            {"chapter_number": 0, "event": "林星入职深空观测站"},
            {"chapter_number": 0, "event": "首次捕捉到异常信号"},
            {"chapter_number": 1, "event": "陈博士开始解读信号"},
        ]
    if with_world:
        vault["world"] = [
            {
                "name": "量子纠缠通讯",
                "constraint": "信息传递速度上限为光速的10倍",
                "description": "基于量子纠缠原理实现的超光速通讯技术",
            },
        ]
    return vault


# ============================================================================
# 测试类
# ============================================================================


class TestPromptAssembly:
    """§3.5 Prompt分层组装 完整测试."""

    @pytest.fixture(autouse=True)
    def _service(self):
        """每个测试方法前实例化 GenerationService."""
        from app.service.generation_service import GenerationService
        self.service = GenerationService()

    # ---- Layer 0 ----

    def test_layer0_system_instruction_present(self):
        """Layer 0: 系统指令必须存在且包含章节号."""
        project = _make_project()
        chapter = _make_chapter()
        outline = _make_outline()
        vault = _make_vault()

        prompt = self.service._build_generation_prompt(
            project, chapter, outline, "inspiration", vault
        )

        assert "你是一位专业的网络小说作家。" in prompt
        assert "撰写第1章" in prompt or "撰写第1 章" in prompt

    def test_layer0_default_chapter_number_when_missing(self):
        """Layer 0: 章节号缺失时降级为 ?."""
        project = _make_project()
        outline = _make_outline(chapter_number=None)  # type: ignore[arg-type]
        vault = _make_vault()

        prompt = self.service._build_generation_prompt(
            project, None, outline, "inspiration", vault
        )

        assert "撰写第?章" in prompt

    # ---- Layer 1 ----

    def test_layer1_summary_present(self):
        """Layer 1: 前情摘要被正确注入."""
        project = _make_project()
        chapter = _make_chapter()
        outline = _make_outline()
        vault = _make_vault()

        prompt = self.service._build_generation_prompt(
            project, chapter, outline, "inspiration", vault
        )

        # Format changed to prompt_service style (=== Layer 1 === / 【锚点】...)
        assert "林星收到一段来自未知文明的加密信号" in prompt
        assert "视点：林星" in prompt
        assert "地点：深空观测站·阿尔法区" in prompt
        assert "时间：星际历217年·秋" in prompt

    def test_layer1_must_hold_and_must_not(self):
        """Layer 1: 连贯性基线硬约束."""
        project = _make_project()
        chapter = _make_chapter()
        outline = _make_outline()
        vault = _make_vault()

        prompt = self.service._build_generation_prompt(
            project, chapter, outline, "inspiration", vault
        )

        assert "必须保持" in prompt
        assert "林星拥有信号解读能力" in prompt
        assert "必须避免" in prompt
        assert "陈博士突然回归" in prompt

    def test_layer1_unresolved_hooks_top3(self):
        """Layer 1: 未收束钩子仅显示 Top3."""
        project = _make_project()
        chapter = _make_chapter()
        outline = _make_outline()
        vault = _make_vault()
        # Add extra hooks
        vault["dynamic_layer"]["unresolved_hooks"] = [
            {"description": f"Hook {i}"} for i in range(5)
        ]

        prompt = self.service._build_generation_prompt(
            project, chapter, outline, "inspiration", vault
        )

        assert "【未收束钩子】" in prompt
        assert "Hook 0" in prompt
        assert "Hook 2" in prompt
        assert "Hook 3" not in prompt  # prompt_service caps at 3 via build_layer1

    def test_layer1_dynamic_layer_none(self):
        """Layer 1: dynamic_layer 为 None 时不报错."""
        project = _make_project()
        chapter = _make_chapter()
        outline = _make_outline()
        vault = _make_vault(with_dynamic_layer=False)

        prompt = self.service._build_generation_prompt(
            project, chapter, outline, "inspiration", vault
        )

        # Anchor defaults when no dynamic layer
        assert "视点：不限" in prompt

    # ---- Layer 2 ----

    def test_layer2_characters_present(self):
        """Layer 2: 人物设定注入."""
        project = _make_project()
        chapter = _make_chapter()
        outline = _make_outline()
        vault = _make_vault()

        prompt = self.service._build_generation_prompt(
            project, chapter, outline, "inspiration", vault
        )

        # Layer 2 uses prompt_service format: 【角色信息】, bullet-list entries
        assert "=== Layer 2 ===" in prompt
        assert "林星" in prompt
        assert "protagonist" in prompt
        assert "焦虑不安" in prompt
        assert "陈博士" in prompt

    def test_layer2_promises_present(self):
        """Layer 2: 剧情承诺注入."""
        project = _make_project()
        chapter = _make_chapter()
        outline = _make_outline()
        vault = _make_vault()

        prompt = self.service._build_generation_prompt(
            project, chapter, outline, "inspiration", vault
        )

        assert "【相关伏笔】" in prompt
        assert "神秘信号来源之谜" in prompt
        assert "紧迫度" in prompt

    def test_layer2_timeline_present(self):
        """Layer 2: 时间线参考注入."""
        project = _make_project()
        chapter = _make_chapter()
        outline = _make_outline()
        vault = _make_vault()

        prompt = self.service._build_generation_prompt(
            project, chapter, outline, "inspiration", vault
        )

        assert "【时间线参考】" in prompt
        assert "林星入职深空观测站" in prompt
        assert "首次捕捉到异常信号" in prompt

    def test_layer2_world_present(self):
        """Layer 2: 世界观规则注入."""
        project = _make_project()
        chapter = _make_chapter()
        outline = _make_outline()
        vault = _make_vault()

        prompt = self.service._build_generation_prompt(
            project, chapter, outline, "inspiration", vault
        )

        assert "【世界观规则】" in prompt
        assert "量子纠缠通讯" in prompt
        assert "光速的10倍" in prompt

    def test_layer2_all_empty(self):
        """Layer 2: 所有四库为空时优雅降级."""
        project = _make_project()
        chapter = _make_chapter()
        outline = _make_outline()
        vault = _make_vault(
            with_chars=False, with_promises=False,
            with_timeline=False, with_world=False,
        )

        prompt = self.service._build_generation_prompt(
            project, chapter, outline, "inspiration", vault
        )

        # Layer 2 all empty: sections should not appear
        assert "=== Layer 2 ===" in prompt
        # Sections without data use placeholder text "(暂无 vault 数据)" or "(暂无卡牌方向)"
        assert "【角色信息】" not in prompt  # no data → no section header with data
        assert "【相关伏笔】" not in prompt
        assert "【时间线参考】" not in prompt
        assert "【世界观规则】" not in prompt

    # ---- Layer 3 ----

    def test_layer3_directions_present(self):
        """Layer 3: 卡片方向注入."""
        project = _make_project()
        chapter = _make_chapter()
        outline = _make_outline()
        vault = _make_vault()

        prompt = self.service._build_generation_prompt(
            project, chapter, outline, "inspiration", vault
        )

        assert "=== Layer 3 ===" in prompt
        assert "【卡牌融合方向】" in prompt
        assert "主角觉醒" in prompt
        assert "权重: 1.00" in prompt

    def test_layer3_weaving_scheme(self):
        """Layer 3: 编织方案注入."""
        project = _make_project()
        chapter = _make_chapter()
        outline = _make_outline(
            weaving_scheme={
                "name": "双线交织",
                "description": "林星和陈博士的线索交替推进",
            }
        )
        vault = _make_vault()

        prompt = self.service._build_generation_prompt(
            project, chapter, outline, "inspiration", vault
        )

        # prompt_service uses description not name for weaving scheme
        assert "编织方案" in prompt
        assert "林星和陈博士的线索交替推进" in prompt

    def test_layer3_inspiration_present(self):
        """Layer 3: 创作灵感注入."""
        project = _make_project()
        chapter = _make_chapter()
        outline = _make_outline()
        vault = _make_vault()

        prompt = self.service._build_generation_prompt(
            project, chapter, outline, "测试灵感：危机中的转机", vault
        )

        assert "【创作灵感】" in prompt
        assert "测试灵感：危机中的转机" in prompt

    # ---- 写作要求 ----

    def test_writing_requirements(self):
        """写作要求包含字数、钩子等约束."""
        project = _make_project()
        chapter = _make_chapter()
        outline = _make_outline()
        vault = _make_vault()

        prompt = self.service._build_generation_prompt(
            project, chapter, outline, "inspiration", vault
        )

        assert "【写作要求】" in prompt
        assert "字数 2500-3500" in prompt
        assert "结尾留钩子" in prompt
        assert "至少推进一个未收束悬念" in prompt

    # ---- 降级/异常场景 ----

    def test_outline_without_required_keys(self):
        """outline 缺少部分 key 时不报错."""
        project = _make_project()
        chapter = _make_chapter()
        # minimal outline — only what must be there
        outline: Dict[str, Any] = {
            "chapter_title": "启程",
            "chapter_number": 1,
            "selected_directions": [],
            "characters": [],
            "generation_requirements": {
                "word_count": "2500-3500",
            },
        }
        vault = _make_vault()

        # 不应抛异常
        prompt = self.service._build_generation_prompt(
            project, chapter, outline, "", vault
        )

        assert "你是一位专业的网络小说作家。" in prompt
        assert "=== Layer 1 ===" in prompt
        assert "=== Layer 2 ===" in prompt
        assert "=== Layer 3 ===" in prompt

    def test_completely_empty_vault(self):
        """relevant_vault 为空字典时不报错."""
        project = _make_project()
        chapter = _make_chapter()
        outline = _make_outline(
            selected_directions=[],
            characters=[],
            recent_events=[],
        )
        vault: Dict[str, Any] = {}

        prompt = self.service._build_generation_prompt(
            project, chapter, outline, "", vault
        )

        # All four layer markers present in prompt_service format
        assert "=== Layer 0 ===" in prompt
        assert "=== Layer 1 ===" in prompt
        assert "=== Layer 2 ===" in prompt
        assert "=== Layer 3 ===" in prompt

    def test_backward_compatibility_old_format(self):
        """向后兼容: 旧数据格式（没有 dynamic_layer）仍可工作."""
        project = _make_project()
        chapter = _make_chapter()
        outline = _make_outline()
        # relevant_vault 不使用 dynamic_layer 子结构
        vault = {
            "characters": [{"name": "林星", "description": "主角"}],
        }

        prompt = self.service._build_generation_prompt(
            project, chapter, outline, "inspiration", vault
        )

        assert "【角色信息】" in prompt
        assert "林星" in prompt

    def test_full_prompt_structure_order(self):
        """验证 prompt 的各部分严格按文档顺序排列."""
        project = _make_project()
        chapter = _make_chapter()
        outline = _make_outline()
        vault = _make_vault()

        prompt = self.service._build_generation_prompt(
            project, chapter, outline, "inspiration", vault
        )

        # 检查各层出现顺序（prompt_service format: === Layer X ===）
        pos_layer0 = prompt.index("你是一位专业的网络小说作家")
        pos_layer1 = prompt.index("=== Layer 1 ===")
        pos_layer2 = prompt.index("=== Layer 2 ===")
        pos_layer3 = prompt.index("=== Layer 3 ===")
        pos_req = prompt.index("【写作要求】")

        assert pos_layer0 < pos_layer1, "Layer 0 必须在 Layer 1 之前"
        assert pos_layer1 < pos_layer2, "Layer 1 必须在 Layer 2 之前"
        assert pos_layer2 < pos_layer3, "Layer 2 必须在 Layer 3 之前"
        assert pos_layer3 < pos_req, "Layer 3 必须在 写作要求 之前"

    def test_separator_lines_present(self):
        """每个关键区域之间都有 '=' 分隔线."""
        project = _make_project()
        chapter = _make_chapter()
        outline = _make_outline()
        vault = _make_vault()

        prompt = self.service._build_generation_prompt(
            project, chapter, outline, "inspiration", vault
        )

        # At least 4 "=== Layer X ===" markers (Layers 0-3)
        assert prompt.count("=== Layer") >= 4
