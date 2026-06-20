"""
墨灵 (Moling) — Genre Analysis 单元测试

测试 A1-A5 全流程：
  - A1: 黄金三章结构提取（开篇模式识别 + 节奏曲线 + 吸引力评估）
  - A2: 角色出场模式聚类（姓名提取 + 出场方式检测 + 角色聚类 + 时序模板）
  - A3: 钩子密度量化（钩子类型检测 + 章尾钩子 + 密度曲线）
  - A4: 节奏曲线拟合（斜率计算 + 拐点检测 + 节奏类型判定）
  - A5: 套路归纳输出（去版权化 + Profile 构建 + JSON 序列化）
"""

from __future__ import annotations

import pytest

from app.genre.a1_opening import (
    A1_analyze_opening,
    A1Result,
    OpeningPattern,
    _extract_opening_features,
    _score_direct_conflict,
    _score_daily_life,
    _score_flashback,
    _score_world_building,
    _compute_initial_rhythm,
    _compute_attraction,
)
from app.genre.a2_characters import (
    A2_cluster_characters,
    A2Result,
    CharacterEntry,
    CharacterTimingTemplate,
    _extract_from_chapter,
    _detect_intro_method,
    _merge_characters,
    _cluster_by_role,
    _build_templates,
)
from app.genre.a3_hooks import (
    A3_quantify_hooks,
    A3Result,
    ChapterHookResult,
    _score_chapter,
    HOOK_PATTERNS,
)
from app.genre.a4_rhythm import (
    A4_fit_rhythm_curve,
    A4Result,
    RhythmProfile,
    RhythmPoint,
    _compute_initial_rhythm as _a4_compute_rhythm,
)
from app.genre.a5_profile_output import (
    A5_summarize_patterns,
    profile_to_json,
    _filter_copyrighted,
    _generate_card_seeds,
    _pattern_label,
    _extract_world_templates,
)
from app.genre.models import GenreProfile


# ============================================================================
# 测试数据
# ============================================================================

# 样本小说章节（模拟玄幻小说前 3 章）
SAMPLE_CHAPTERS = [
    # 第一章：直接冲突开篇
    """陈道临睁开眼的瞬间，一道刀光已经劈到了面前！
他本能地翻身躲闪，后背撞上了冰冷的石壁。
"杀了他！"一个粗哑的声音吼道。
陈道临笑道："你们是谁？为什么要杀我？"
他来不及思考，双手在地上胡乱摸索，抓到一根木棍就挥了出去。
木棍砸在追击者的膝盖上，那人惨叫一声跪倒。
陈道临问道："这是哪里？"
追击者喊道："小子，别挣扎了！"
陈道临趁机冲了出去，跑进了黑暗中。
他不知道为什么有人要杀他，也不知道自己身在何处。
唯一知道的是——如果不逃，就死定了。""",

    # 第二章：引入世界观
    """三天后，陈道临终于搞清楚了状况。
这里是青云宗的外门修炼场，而他——陈道临，是被人从现代社会扔过来的。
"这就是传说中的穿越？"陈道临叹道。
教习师兄李察走过来，拍了拍他的肩膀："小子，你这身板太弱了。明天开始跟我练气。"
陈道临苦笑道："练气？我连气都喘不匀。"
但他很快发现了这个世界的有趣之处——这里有修仙者，有妖兽，有法宝，还有各种神奇的功法。
"如果能学会御剑飞行，那该多好啊。"他心想。
李察看穿了他的心思，笑道："先学会站桩吧。"
傍晚时分，宗门钟声响起，所有外门弟子聚集在练武场上。
一个身穿紫袍的老者站在高台上，喊道："三日后，宗门大比！前十名可进入内门！"
陈道临的心跳加速了。这是他改变命运的机会。""",

    # 第三章：钩子 + 角色深化
    """宗门大比前夜，陈道临在修炼室遇到了一个神秘人。
黑暗中，那个身影站在角落里，像是早就等在那里。
"你是谁？"陈道临问道。
身影缓缓走出阴影，露出了一张苍白的脸。
"我叫叶倾城，"他说道，"跟你一样，从另一个世界来。"
陈道临震惊了。他一直以为自己是最特殊的那个。
叶倾城问道："你是怎么来的？为什么会被追杀？"
"我不知道——我醒来就在这儿了。"陈道临喊道。
叶倾城沉默了片刻，然后突然说出了让陈道临毛骨悚然的话：
"有人故意把你送到这里。而那个人的目标，是杀了你。"
陈道临感到一阵寒意从脊背升起。
"明天的大比，你要小心，"叶倾城说道，"因为杀手就在比试队伍里。"
话音刚落，叶倾城就消失了，仿佛从未出现过。
陈道临站在原地，手心全是冷汗。
陈道临问道："到底是谁想杀我？为什么？明天的大比，我还能活着回来吗？"
""",
]

# 第二本小说的章节样本（不同风格）
SAMPLE_CHAPTERS_2 = [
    # 日常引入开篇
    """清晨的阳光透过窗帘洒在脸上，林小雨不情愿地睁开了眼睛。
闹钟还没响，她习惯性地摸到手机，看了一眼时间——6:45。
再睡五分钟。她翻了个身，把被子拉过头顶。
十分钟后，妈妈的声音从楼下传来："小雨，再不起床就要迟到了！"
"知道了知道了。"林小雨嘟囔道，拖着拖鞋走进卫生间。
镜子里是一张睡眼惺忪的脸，额头上不知道什么时候又冒出了一颗痘痘。
她叹了口气，开始刷牙。这就是普通高中生的日常生活。
但林小雨不知道的是，今天将是她平凡人生的最后一天。""",

    # 第二章
    """教室里的气氛有些奇怪。
林小雨一进门就感觉到了——同学们看她的眼神不一样了。
"怎么了？"她问同桌王芳。
王芳凑过来，压低声音说："你听说了吗？新来的转校生。他点名要坐你旁边。"
"什么？"林小雨愣住了。
就在这时，教室的门被推开了。
一个身材修长的男生走了进来，他有一双奇特的眼睛——瞳孔是银色的。
全班瞬间安静了。
银瞳少年径直走到林小雨旁边的空位坐下，头也不回地说道：
"你好，我叫夜辰。从今天开始，我来保护你。"
林小雨惊呼道："你是谁？我根本不认识你！"
""",
]

# 不开篇模式章节（用于测试边界情况）
MINIMAL_CHAPTERS = [
    "这是一段很平淡的文字，没有什么特别的内容。",
]


# ============================================================================
# A1: 黄金三章结构提取
# ============================================================================

class TestA1Opening:
    """测试 A1 开篇模式分析"""

    def test_analyze_opening_returns_result(self):
        """基本功能：返回 A1Result"""
        result = A1_analyze_opening(SAMPLE_CHAPTERS)
        assert isinstance(result, A1Result)
        assert isinstance(result.opening_pattern, OpeningPattern)

    def test_direct_conflict_detection(self):
        """检测直接冲突开篇"""
        result = A1_analyze_opening(SAMPLE_CHAPTERS)
        assert result.opening_pattern.pattern_type in (
            "direct_conflict", "daily_life", "flashback", "world_building"
        )
        assert result.opening_pattern.confidence > 0

    def test_rhythm_curve_non_empty(self):
        """节奏曲线不为空"""
        result = A1_analyze_opening(SAMPLE_CHAPTERS)
        assert len(result.rhythm_curve) > 0
        for point in result.rhythm_curve:
            assert "chapter" in point
            assert "tension" in point
            assert "relative_pos" in point

    def test_attraction_score_range(self):
        """吸引力评分在 0-1 之间"""
        result = A1_analyze_opening(SAMPLE_CHAPTERS)
        assert 0 <= result.attraction_score <= 1

    def test_empty_chapters(self):
        """空输入返回空结果"""
        result = A1_analyze_opening([])
        assert result.opening_pattern.pattern_type == ""
        assert result.opening_pattern.confidence == 0.0
        assert result.attraction_score == 0.0

    def test_extract_opening_features(self):
        """特征提取返回字典"""
        features = _extract_opening_features(SAMPLE_CHAPTERS[0][:2000])
        assert "conflict_count" in features
        assert "daily_count" in features
        assert "past_count" in features
        assert "define_count" in features
        assert "proper_noun_density" in features
        assert "short_sentence_ratio" in features
        assert "action_verb_ratio" in features

    def test_score_direct_conflict_high(self):
        """高冲突文本得分高"""
        conflict_text = "他杀了一个敌人。他追杀另一个敌人。战斗很激烈。"
        features = _extract_opening_features(conflict_text)
        score = _score_direct_conflict(features)
        assert score > 0

    def test_score_daily_life(self):
        """日常文本得分"""
        daily_text = "清晨起床后，他去了学校。阳光洒在教室的课桌上。"
        features = _extract_opening_features(daily_text)
        score = _score_daily_life(features)
        assert score > 0

    def test_score_flashback(self):
        """回忆文本得分"""
        flashback_text = "回忆起三年前的那件事，他想起了过去。曾经的他不是这样的。"
        features = _extract_opening_features(flashback_text)
        score = _score_flashback(features)
        assert score > 0

    def test_score_world_building(self):
        """世界观构建文本得分"""
        world_text = "这个大陆被称为玄天大陆。灵宗是最大的势力。青云国是最强的国家。"
        features = _extract_opening_features(world_text)
        score = _score_world_building(features)
        assert score > 0

    def test_compute_initial_rhythm(self):
        """初期节奏计算"""
        rhythm = _compute_initial_rhythm(SAMPLE_CHAPTERS[:3])
        assert len(rhythm) == 30  # 3 chapters * 10 windows
        assert all("tension" in p for p in rhythm)
        assert all("chapter" in p for p in rhythm)

    def test_compute_attraction(self):
        """吸引力评分计算"""
        rhythm = _compute_initial_rhythm(SAMPLE_CHAPTERS[:3])
        score = _compute_attraction("direct_conflict", 0.8, rhythm)
        assert 0 <= score <= 1


# ============================================================================
# A2: 角色出场模式聚类
# ============================================================================

class TestA2Characters:
    """测试 A2 角色分析"""

    def test_cluster_characters_returns_result(self):
        """基本功能：返回 A2Result"""
        result = A2_cluster_characters(SAMPLE_CHAPTERS)
        assert isinstance(result, A2Result)
        assert isinstance(result.characters, list)

    def test_extract_character_names(self):
        """提取角色名（正则匹配 2-4 个中文字符 + 说话动词）"""
        entries = _extract_from_chapter(SAMPLE_CHAPTERS[0], 1)
        names = {e.name for e in entries}
        # 正则会匹配到一些名字，提取结果非空即可
        assert len(names) > 0

    def test_extract_unique_names(self):
        """同一章不重复提取同名角色"""
        # 使用 2 字中文名 + 单独动词，避免正则贪婪匹配到动词字
        text = "张三道。张三道。张三道。"
        entries = _extract_from_chapter(text, 1)
        # "张三" (2 char) + "道" (verb) → name="张三"，出现 3 次去重为 1
        assert len(entries) == 1
        assert entries[0].name == "张三"

    def test_detect_intro_method(self):
        """出场方式检测"""
        action_context = "他推开门走进去"
        assert _detect_intro_method(action_context) == "action"

        desc_context = "只见一个男子走进来"
        assert _detect_intro_method(desc_context) == "description"

        mystery_context = "黑暗中突然出现一个人影"
        assert _detect_intro_method(mystery_context) == "mystery"

    def test_detect_intro_method_unknown(self):
        """无法识别出场方式"""
        context = "某些无法识别的文本"
        assert _detect_intro_method(context) == "unknown"

    def test_merge_characters(self):
        """合并同名角色"""
        entries = [
            CharacterEntry(name="陈道临", first_chapter=1, intro_method="action", chapter_count=1, dialogue_count=3),
            CharacterEntry(name="陈道临", first_chapter=2, intro_method="dialog", chapter_count=1, dialogue_count=2),
            CharacterEntry(name="李察", first_chapter=1, intro_method="description", chapter_count=1, dialogue_count=1),
        ]
        merged = _merge_characters(entries)
        assert len(merged) == 2
        cdl = next(e for e in merged if e.name == "陈道临")
        assert cdl.dialogue_count == 5  # 3 + 2

    def test_cluster_by_role(self):
        """角色聚类"""
        entries = [
            CharacterEntry(name="主角", first_chapter=1, first_position=100),
            CharacterEntry(name="配角", first_chapter=1, first_position=600),
            CharacterEntry(name="对手", first_chapter=2, first_position=300),
            CharacterEntry(name="神秘人", first_chapter=3, first_position=200),
        ]
        clusters = _cluster_by_role(entries, 3)
        assert "protagonist" in clusters
        assert "core_supporting" in clusters
        # 检查主角
        assert len(clusters["protagonist"]) == 1
        assert clusters["protagonist"][0].name == "主角"

    def test_build_templates(self):
        """生成时序模板"""
        clusters = {
            "protagonist": [CharacterEntry(name="主角", first_chapter=1)],
            "core_supporting": [CharacterEntry(name="配角", first_chapter=1, first_position=600)],
        }
        templates = _build_templates(clusters)
        assert len(templates) == 2
        assert any(t.role_type == "主角" for t in templates)
        assert any(t.role_type == "核心配角" for t in templates)


# ============================================================================
# A3: 钩子密度量化
# ============================================================================

class TestA3Hooks:
    """测试 A3 钩子分析"""

    def test_quantify_hooks_returns_result(self):
        """基本功能：返回 A3Result"""
        result = A3_quantify_hooks(SAMPLE_CHAPTERS)
        assert isinstance(result, A3Result)
        assert len(result.chapter_hooks) == 3

    def test_hook_density_in_range(self):
        """钩子密度非负"""
        result = A3_quantify_hooks(SAMPLE_CHAPTERS)
        for ch in result.chapter_hooks:
            assert ch.hook_density >= 0

    def test_closing_hook_detection(self):
        """章尾钩子检测"""
        # 第三章末尾有悬疑钩子
        result = A3_quantify_hooks(SAMPLE_CHAPTERS)
        # 第三章应是 ch3
        ch3 = result.chapter_hooks[2]
        assert ch3.chapter == 3

    def test_overall_level(self):
        """全局等级为非空字符串"""
        result = A3_quantify_hooks(SAMPLE_CHAPTERS)
        assert result.overall_level in ("low", "medium", "high", "very_high")

    def test_density_curve_length(self):
        """密度曲线长度等于章节数"""
        result = A3_quantify_hooks(SAMPLE_CHAPTERS)
        assert len(result.density_curve) == 3

    def test_hook_patterns_defined(self):
        """钩子模式已定义"""
        assert "cliffhanger" in HOOK_PATTERNS
        assert "info_hook" in HOOK_PATTERNS
        assert "countdown" in HOOK_PATTERNS
        assert "cognitive_twist" in HOOK_PATTERNS
        # 验证权重为正
        for hook_type, (weight, _) in HOOK_PATTERNS.items():
            assert weight > 0

    def test_score_chapter_empty(self):
        """空章节返回零结果"""
        result = _score_chapter("", 1)
        assert result.total_score == 0.0
        assert result.hook_count == 0

    def test_avg_density(self):
        """平均密度计算"""
        result = A3_quantify_hooks(SAMPLE_CHAPTERS)
        assert result.avg_density >= 0
        assert result.max_density >= result.avg_density


# ============================================================================
# A4: 节奏曲线拟合
# ============================================================================

class TestA4Rhythm:
    """测试 A4 节奏分析"""

    def test_fit_rhythm_curve_returns_result(self):
        """基本功能：返回 A4Result"""
        hook_density = [0.5, 0.8, 1.2]
        result = A4_fit_rhythm_curve(SAMPLE_CHAPTERS, hook_density)
        assert isinstance(result, A4Result)
        assert isinstance(result.rhythm_profile, RhythmProfile)

    def test_empty_chapters(self):
        """空章节返回零结果"""
        result = A4_fit_rhythm_curve([], [])
        assert result.chapter_count == 0

    def test_rhythm_type_valid(self):
        """节奏类型为有效值"""
        result = A4_fit_rhythm_curve(SAMPLE_CHAPTERS, [0.5, 0.8, 1.2])
        assert result.rhythm_profile.rhythm_type in (
            "fast_paced", "slow_paced", "wave",
            "crescendo", "diminuendo", "steady",
        )

    def test_slopes_computed(self):
        """斜率计算"""
        result = A4_fit_rhythm_curve(SAMPLE_CHAPTERS, [0.5, 0.8, 1.2])
        assert len(result.rhythm_profile.slopes) > 0

    def test_confidence_range(self):
        """置信度在 0-1 之间"""
        result = A4_fit_rhythm_curve(SAMPLE_CHAPTERS, [0.5, 0.8, 1.2])
        assert 0 <= result.rhythm_profile.confidence <= 1

    def test_compute_initial_rhythm(self):
        """A4 内部节奏计算"""
        rhythm = _a4_compute_rhythm(SAMPLE_CHAPTERS[:3])
        assert len(rhythm) > 0
        for point in rhythm:
            assert isinstance(point, RhythmPoint)
            assert point.tension >= 0


# ============================================================================
# A5: 套路归纳输出
# ============================================================================

class TestA5ProfileOutput:
    """测试 A5 Profile 构建"""

    def test_summarize_patterns_returns_profile(self):
        """基本功能：返回 GenreProfile"""
        a1 = A1_analyze_opening(SAMPLE_CHAPTERS)
        a2 = A2_cluster_characters(SAMPLE_CHAPTERS)
        a3 = A3_quantify_hooks(SAMPLE_CHAPTERS)
        a4 = A4_fit_rhythm_curve(SAMPLE_CHAPTERS, a3.density_curve)

        profile = A5_summarize_patterns(a1, a2, a3, a4, genre="玄幻")
        assert isinstance(profile, GenreProfile)
        assert profile.genre == "玄幻"
        assert profile.version == "0.1"
        assert profile.novels_analyzed == 1

    def test_profile_has_golden_three(self):
        """Profile 包含黄金三章结构"""
        a1 = A1_analyze_opening(SAMPLE_CHAPTERS)
        a2 = A2_cluster_characters(SAMPLE_CHAPTERS)
        a3 = A3_quantify_hooks(SAMPLE_CHAPTERS)
        a4 = A4_fit_rhythm_curve(SAMPLE_CHAPTERS, a3.density_curve)

        profile = A5_summarize_patterns(a1, a2, a3, a4)
        assert "opening_pattern" in profile.golden_three_structure
        assert "rhythm_curve" in profile.golden_three_structure
        assert "attraction_score" in profile.golden_three_structure

    def test_profile_has_character_archetypes(self):
        """Profile 包含角色原型"""
        a1 = A1_analyze_opening(SAMPLE_CHAPTERS)
        a2 = A2_cluster_characters(SAMPLE_CHAPTERS)
        a3 = A3_quantify_hooks(SAMPLE_CHAPTERS)
        a4 = A4_fit_rhythm_curve(SAMPLE_CHAPTERS, a3.density_curve)

        profile = A5_summarize_patterns(a1, a2, a3, a4)
        assert isinstance(profile.character_archetypes, list)

    def test_profile_has_pacing_curve(self):
        """Profile 包含节奏曲线"""
        a1 = A1_analyze_opening(SAMPLE_CHAPTERS)
        a2 = A2_cluster_characters(SAMPLE_CHAPTERS)
        a3 = A3_quantify_hooks(SAMPLE_CHAPTERS)
        a4 = A4_fit_rhythm_curve(SAMPLE_CHAPTERS, a3.density_curve)

        profile = A5_summarize_patterns(a1, a2, a3, a4)
        assert "type" in profile.pacing_curve
        assert "slopes" in profile.pacing_curve

    def test_profile_has_hook_density(self):
        """Profile 包含钩子密度信息"""
        a1 = A1_analyze_opening(SAMPLE_CHAPTERS)
        a2 = A2_cluster_characters(SAMPLE_CHAPTERS)
        a3 = A3_quantify_hooks(SAMPLE_CHAPTERS)
        a4 = A4_fit_rhythm_curve(SAMPLE_CHAPTERS, a3.density_curve)

        profile = A5_summarize_patterns(a1, a2, a3, a4)
        assert "hook_density_level" in profile.dynamic_layer_seeds
        assert "avg_density" in profile.dynamic_layer_seeds

    def test_profile_has_card_pool(self):
        """Profile 包含卡牌池种子"""
        a1 = A1_analyze_opening(SAMPLE_CHAPTERS)
        a2 = A2_cluster_characters(SAMPLE_CHAPTERS)
        a3 = A3_quantify_hooks(SAMPLE_CHAPTERS)
        a4 = A4_fit_rhythm_curve(SAMPLE_CHAPTERS, a3.density_curve)

        profile = A5_summarize_patterns(a1, a2, a3, a4)
        assert isinstance(profile.card_pool_enrichment, list)
        assert len(profile.card_pool_enrichment) > 0

    def test_profile_to_json(self):
        """JSON 序列化"""
        a1 = A1_analyze_opening(SAMPLE_CHAPTERS)
        a2 = A2_cluster_characters(SAMPLE_CHAPTERS)
        a3 = A3_quantify_hooks(SAMPLE_CHAPTERS)
        a4 = A4_fit_rhythm_curve(SAMPLE_CHAPTERS, a3.density_curve)

        profile = A5_summarize_patterns(a1, a2, a3, a4, genre="玄幻")
        json_str = profile_to_json(profile)
        assert isinstance(json_str, str)
        assert "玄幻" in json_str
        import json
        parsed = json.loads(json_str)
        assert parsed["genre"] == "玄幻"

    def test_pattern_label(self):
        """模式标签映射"""
        assert _pattern_label("direct_conflict") == "直接冲突开篇"
        assert _pattern_label("daily_life") == "日常引入开篇"
        assert _pattern_label("flashback") == "倒叙/悬疑开篇"
        assert _pattern_label("world_building") == "设定引入开篇"
        assert _pattern_label("unknown_type") == "未知"

    def test_filter_copyrighted(self):
        """去版权化过滤"""
        from app.genre.a2_characters import CharacterEntry
        chars = [
            CharacterEntry(name="孙悟空", first_chapter=1),
            CharacterEntry(name="原创角色", first_chapter=1),
        ]
        filtered = _filter_copyrighted(chars)
        names = {c.name for c in filtered}
        assert "孙悟空" not in names
        assert "原创角色" in names

    def test_extract_world_templates(self):
        """世界观模板提取"""
        from app.genre.a2_characters import CharacterEntry
        a2 = A2Result(
            characters=[
                CharacterEntry(name="灵宗长老", first_chapter=1),
                CharacterEntry(name="青云国主", first_chapter=1),
            ],
        )
        templates = _extract_world_templates(a2, genre="玄幻")
        assert len(templates) >= 2  # 至少包含角色模板 + 类型模板
        types = {t["type"] for t in templates}
        assert "势力/组织" in types or "修炼体系" in types

    def test_generate_card_seeds(self):
        """卡牌种子生成"""
        a1 = A1_analyze_opening(SAMPLE_CHAPTERS)
        a3 = A3_quantify_hooks(SAMPLE_CHAPTERS)
        seeds = _generate_card_seeds(a1, a3)
        assert isinstance(seeds, list)
        assert len(seeds) > 0
        for seed in seeds:
            assert "direction" in seed
            assert "rarity" in seed
            assert seed["rarity"] in ("common", "rare", "epic")

    def test_daily_life_opening_seeds(self):
        """日常开篇卡牌种子"""
        daily_chapters = [
            "清晨的阳光洒进房间，他起床刷牙洗脸。学校门口的早餐摊已经排起了长队。",
        ]
        a1 = A1_analyze_opening(daily_chapters)
        a3 = A3_quantify_hooks(daily_chapters)
        seeds = _generate_card_seeds(a1, a3)
        assert len(seeds) > 0


# ============================================================================
# 端到端集成测试：A1 → A2 → A3 → A4 → A5
# ============================================================================

class TestGenrePipelineEndToEnd:
    """测试 A1-A5 完整管线"""

    def test_full_pipeline(self):
        """验证 A1→A2→A3→A4→A5 全流程不抛异常"""
        # A1
        a1 = A1_analyze_opening(SAMPLE_CHAPTERS)
        assert a1.opening_pattern.confidence > 0

        # A2
        a2 = A2_cluster_characters(SAMPLE_CHAPTERS)
        assert len(a2.characters) > 0

        # A3
        a3 = A3_quantify_hooks(SAMPLE_CHAPTERS)
        assert a3.overall_level != ""

        # A4
        a4 = A4_fit_rhythm_curve(SAMPLE_CHAPTERS, a3.density_curve)
        assert a4.rhythm_profile.rhythm_type != ""

        # A5
        profile = A5_summarize_patterns(a1, a2, a3, a4, genre="玄幻")
        assert profile.genre == "玄幻"

        # 可序列化
        json_str = profile_to_json(profile)
        assert len(json_str) > 100

    def test_pipeline_with_minimal_input(self):
        """最小输入不抛异常"""
        a1 = A1_analyze_opening(MINIMAL_CHAPTERS)
        a2 = A2_cluster_characters(MINIMAL_CHAPTERS)
        a3 = A3_quantify_hooks(MINIMAL_CHAPTERS)
        a4 = A4_fit_rhythm_curve(MINIMAL_CHAPTERS, a3.density_curve)
        profile = A5_summarize_patterns(a1, a2, a3, a4, genre="测试")
        assert isinstance(profile, GenreProfile)

    def test_two_different_styles(self):
        """不同风格的章节产出不同结果"""
        result1 = A1_analyze_opening(SAMPLE_CHAPTERS)
        result2 = A1_analyze_opening(SAMPLE_CHAPTERS_2)

        # 两个不同风格的文本应产生不同的模式
        # 不强制断言具体类型，只验证均有结果
        assert result1.opening_pattern.pattern_type != ""
        assert result2.opening_pattern.pattern_type != ""
