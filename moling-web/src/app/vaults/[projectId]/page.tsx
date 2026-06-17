"use client";

import { useState, useMemo, useEffect, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import { useAuth } from "@/hooks/useAuth";
import { showToast } from "@/components/ui/Toast";
import { Spinner } from "@/components/ui/Spinner";
import { vaultApi } from "@/lib/api";
import type { VaultCharacter, VaultTimeline, VaultPlotPromise, VaultWorld } from "@/lib/types";
import { safeArray, safeObject } from "@/lib/apiSafety";  // ✅ 导入安全工具
import styles from "./page.module.css";

// ── Type Definitions ──

type DTab = "character" | "timeline" | "commitments" | "world" | "secrets";
type CharFilter = "all" | "protagonist" | "ally" | "neutral" | "opponent" | "villain";
type ForeshadowFilter = "all" | "active" | "pending" | "recovered" | "lost";
type WorldFilter = "all" | "geography" | "history" | "magic" | "faction";
type SecretsFilter = "all" | "absolute" | "partial" | "open";
type MobilePlotFilter = "all" | "pending" | "done";
type WorldCatFilter = "all" | "geo" | "his" | "sys" | "power";

interface CharacterDetail {
  name: string;
  faction: string;
  background: string;
  ability: string;
  relationships: string;
  arc: string;
}

interface ForeshadowItem {
  id: string;
  title: string;
  urgency: "high" | "medium" | "low";
  badge: string;
  badgeClass: string;
  status: string;
  statusClass: string;
  chapter: string;
  characters: string;
  suggestChapter: string;
  detailRows: { label: string; value: string }[];
}

interface SecretRow {
  secret: string;
  known: Record<string, boolean | null>;
  level: string;
  debt: number | string;
}

// ── Mock Data ──

const PROJECT_NAME = "苍穹之剑";

const CHAR_FILTER_LABELS: { key: CharFilter; label: string }[] = [
  { key: "all", label: "全部 (18)" },
  { key: "protagonist", label: "主角 (1)" },
  { key: "ally", label: "盟友 (5)" },
  { key: "neutral", label: "中立 (3)" },
  { key: "opponent", label: "对手 (6)" },
  { key: "villain", label: "反派 (3)" },
];

const CHARACTER_CARDS = [
  { name: "苏铭", faction: "protagonist", avatarClass: "protagonist", avatarChar: "苏", chapters: "23", tags: ["坚韧", "重情义", "天赋异禀", "直感型"], status: "宗门考核秘境中", statusDotColor: "var(--color-success)" },
  { name: "长风", faction: "ally", avatarClass: "ally", avatarChar: "长", chapters: "15", tags: ["沉稳", "博学", "神秘", "金灵使"], status: "与主角同行", statusDotColor: "var(--color-success)" },
  { name: "叶灵溪", faction: "ally", avatarClass: "ally", avatarChar: "叶", chapters: "8", tags: ["机敏", "毒舌", "木灵使", "医术"], status: "秘境中东区探索", statusDotColor: "var(--color-success)" },
  { name: "萧远", faction: "ally", avatarClass: "ally", avatarChar: "萧", chapters: "6", tags: ["豪爽", "老兵", "忠诚"], status: "镇守王城东门", statusDotColor: "var(--color-success)" },
  { name: "白鹿", faction: "ally", avatarClass: "ally", avatarChar: "白", chapters: "4", tags: ["温柔", "水灵使", "占卜"], status: "宗门内殿待命", statusDotColor: "var(--color-success)" },
  { name: "顾云栖", faction: "ally", avatarClass: "ally", avatarChar: "顾", chapters: "3", tags: ["少言", "工匠", "机关术"], status: "修缮灵脉阵法", statusDotColor: "var(--color-success)" },
  { name: "灵脉师·无崖", faction: "neutral", avatarClass: "neutral", avatarChar: "灵", chapters: "5", tags: ["超然", "洞察", "守序"], status: "灵脉观测站", statusDotColor: "var(--color-warning)" },
  { name: "商会主·柳如烟", faction: "neutral", avatarClass: "neutral", avatarChar: "商", chapters: "3", tags: ["精明", "八面玲珑", "逐利"], status: "各方势力间斡旋", statusDotColor: "var(--color-warning)" },
  { name: "醉道人", faction: "neutral", avatarClass: "neutral", avatarChar: "酒", chapters: "2", tags: ["癫狂", "深藏不露"], status: "行踪不定", statusDotColor: "var(--color-warning)" },
  { name: "楚天行", faction: "opponent", avatarClass: "opponent", avatarChar: "楚", chapters: "7", tags: ["傲慢", "金灵天才", "世家", "争强好胜"], status: "秘境南区竞争", statusDotColor: "var(--color-warning)" },
  { name: "寒月", faction: "opponent", avatarClass: "opponent", avatarChar: "寒", chapters: "5", tags: ["冷酷", "水灵使", "孤傲"], status: "秘境西区独立行动", statusDotColor: "var(--color-warning)" },
  { name: "赵无极", faction: "opponent", avatarClass: "opponent", avatarChar: "赵", chapters: "4", tags: ["阴狠", "权谋", "御灵级"], status: "暗中操纵考核", statusDotColor: "var(--color-danger)" },
  { name: "帝师·冥渊", faction: "villain", avatarClass: "villain", avatarChar: "帝", chapters: "6", tags: ["野心勃勃", "宗灵级", "操控者", "融灵禁忌"], status: "帝宫密室修炼", statusDotColor: "var(--color-danger)" },
  { name: "血衣使", faction: "villain", avatarClass: "villain", avatarChar: "血", chapters: "4", tags: ["残暴", "执行者", "不死之身"], status: "追踪主角行踪", statusDotColor: "var(--color-danger)" },
  { name: "蛊母", faction: "villain", avatarClass: "villain", avatarChar: "蛊", chapters: "3", tags: ["诡秘", "虫术", "隐匿"], status: "南疆潜伏", statusDotColor: "var(--color-danger)" },
];

const CHARACTER_DETAILS: Record<string, CharacterDetail> = {
  "苏铭": { name: "苏铭", faction: "主角", background: "山村少年，父母早亡，由村长抚养长大。觉醒水灵力后离开村庄，踏上前往王城的旅途。体内灵力异常纯粹，疑似与消失的第八条灵脉有关。", ability: "水灵使 · 初灵三阶（觉醒中）\n特殊能力：水灵变化——可临时改变灵力属性，但代价未知", relationships: "长风（引路人/同伴）· 叶灵溪（考核同伴）· 楚天行（竞争者）· 神秘老者（恩人/谜团）", arc: "觉醒 → 启程 → 考核 → 入宗 → 真相（当前：考核阶段）" },
  "长风": { name: "长风", faction: "盟友", background: "自称游历四方的散修，主动担任苏铭的引路人。对王城和宗门的了解远超常人，真实身份成谜。", ability: "金灵使 · 御灵一阶\n战斗风格以精准打击为主，极少全力出手", relationships: "苏铭（引路对象）· 萧远（旧识？）· 冥渊（立场不明）", arc: "引路人 → 身份揭露 → 立场抉择（当前：潜伏期）" },
  "叶灵溪": { name: "叶灵溪", faction: "盟友", background: "宗门内门弟子，木灵世家出身。表面冷漠，实际热心。擅长以木灵力疗伤。", ability: "木灵使 · 通灵三阶\n擅长治疗和辅助，战斗能力不弱但极少主动进攻", relationships: "苏铭（考核同伴）· 白鹿（闺蜜）· 楚天行（同门，关系冷淡）", arc: "冷漠同伴 → 信任建立 → 并肩作战（当前：信任建立期）" },
  "楚天行": { name: "楚天行", faction: "对手", background: "楚家嫡子，金灵天赋极高，自幼被视为宗门新星。对苏铭这种\"山野之人\"嗤之以鼻。", ability: "金灵使 · 通灵二阶（实际战力接近通灵三阶）\n招式凌厉，攻击性极强", relationships: "苏铭（竞争对手）· 寒月（搭档）· 叶灵溪（同门）", arc: "轻视对手 → 逐渐重视 → 尊重/嫉妒（当前：重视期）" },
  "帝师·冥渊": { name: "帝师·冥渊", faction: "反派", background: "帝国帝师，表面辅佐幼帝，实则是大陆最大的幕后黑手。暗中研究融灵禁术，意图掌控所有灵脉。", ability: "宗灵级（疑似接近圣灵）\n精通金灵与暗灵，暗中掌握融灵之术", relationships: "血衣使（直属部下）· 蛊母（合作者）· 长风（关系成谜）", arc: "幕后操控 → 浮出水面 → 最终对决（当前：幕后操控期）" },
};

const TIMELINE_EVENTS = [
  { day: "第 1 天", text: "主角觉醒灵力，在村中引发异象", className: "completed", isCurrent: false },
  { day: "第 3 天", text: "离开村庄，跟随引路人前往王城", className: "completed", isCurrent: false },
  { day: "第 7 天", text: "抵达王城，初遇宗门考核使", className: "completed", isCurrent: false },
  { day: "第 15 天 · 当前", text: "宗门考核开始，进入试炼秘境", className: "current", isCurrent: true },
  { day: "第 20 天", text: "考核结束，宗门入门仪式（未写）", className: "future", isCurrent: false },
];

const SCENE_LIST = [
  { chapter: "Ch.1", summary: "山村少年日常，夜晚灵力意外觉醒，村中水井沸腾" },
  { chapter: "Ch.3", summary: "神秘老者造访，揭示主角体质特殊，留下玉佩离去" },
  { chapter: "Ch.5", summary: "告别村人，踏上前往王城的旅途" },
  { chapter: "Ch.8", summary: "途经古镇遭遇伏击，首次实战使用水灵力退敌" },
  { chapter: "Ch.12", summary: "地下城战斗，主角在绝境中领悟水灵变化之法" },
  { chapter: "Ch.15", summary: "宗门考核开始，进入试炼秘境，遇见同行对手" },
];

const FORESHADOW_ITEMS: ForeshadowItem[] = [
  { id: "f1", title: "神秘玉佩", urgency: "high", badge: "伏笔", badgeClass: "foreshadow", status: "待回收", statusClass: "pending", chapter: "第3章 · 古墓探索", characters: "主角、神秘老者", suggestChapter: "建议第15-20章回收", detailRows: [{ label: "埋设内容", value: "神秘老者临终前将一枚刻有奇异纹路的玉佩交给主角，称\"此物关乎你身世之谜\"。玉佩在月光下会发出微弱荧光。" }, { label: "预期效果", value: "揭示主角真实身份，连接帝国皇室暗线" }, { label: "关联线索", value: "玉佩纹路与宫中密室符文一致" }] },
  { id: "f2", title: "金灵禁术残卷", urgency: "high", badge: "伏笔", badgeClass: "foreshadow", status: "待回收", statusClass: "pending", chapter: "第7章 · 地下书阁", characters: "主角、长风", suggestChapter: "建议第18-22章回收", detailRows: [{ label: "埋设内容", value: "主角在地下书阁发现残破卷轴，记载了一种可融合金灵与水灵的禁术，但关键页被撕去" }, { label: "预期效果", value: "主角在关键战斗中补全禁术，扭转战局" }, { label: "关联线索", value: "残卷笔迹与老者遗物吻合" }] },
  { id: "f3", title: "王城地下的异响", urgency: "medium", badge: "转折", badgeClass: "twist", status: "待回收", statusClass: "pending", chapter: "第10章 · 王城夜行", characters: "主角", suggestChapter: "建议第20-25章回收", detailRows: [{ label: "埋设内容", value: "主角夜巡王城时听到地下传来规律的低频震动，像是某种巨大生物的心跳" }, { label: "预期效果", value: "引出大陆灵脉危机主线" }, { label: "关联线索", value: "震动频率与灵脉波动吻合" }] },
  { id: "f4", title: "七国密约", urgency: "medium", badge: "推进", badgeClass: "advance", status: "活跃", statusClass: "active", chapter: "第2章 · 旧档室", characters: "长风、萧远", suggestChapter: "建议第25-30章回收", detailRows: [{ label: "埋设内容", value: "七国之间曾有一份密约，约定在灵脉枯竭时共同开启「灵源」。但密约内容各执一词" }] },
  { id: "f5", title: "长风的真实身份", urgency: "low", badge: "伏笔", badgeClass: "foreshadow", status: "活跃", statusClass: "active", chapter: "第5章 · 旅途对话", characters: "长风", suggestChapter: "", detailRows: [{ label: "埋设内容", value: "长风对王城地形极为熟悉，且对宗门内幕了解过多，暗示其身份不简单" }] },
  { id: "f6", title: "消失的第八条灵脉", urgency: "low", badge: "推进", badgeClass: "advance", status: "活跃", statusClass: "active", chapter: "第4章 · 灵脉图", characters: "主角、灵脉师", suggestChapter: "", detailRows: [{ label: "埋设内容", value: "古灵脉图上标注了八条灵脉，但当代只知七条。第八条灵脉的位置被刻意抹去" }] },
  { id: "f7", title: "客栈中的密语", urgency: "low", badge: "收束", badgeClass: "wrap", status: "✓ 已回收", statusClass: "recovered", chapter: "第2章 · 古镇客栈", characters: "", suggestChapter: "", detailRows: [{ label: "回收说明", value: "客栈中听到的密语实际是追杀者传递的暗号，主角在第8章遭遇伏击时恍然大悟" }] },
  { id: "f8", title: "村长的异常举动", urgency: "low", badge: "转折", badgeClass: "twist", status: "✓ 已回收", statusClass: "recovered", chapter: "第1章 · 山村", characters: "", suggestChapter: "", detailRows: [{ label: "回收说明", value: "村长一直阻止主角离开，是因为受人之托暗中保护。告别时村长说的\"别回头\"实为忠告" }] },
  { id: "f9", title: "断桥上的符文", urgency: "high", badge: "伏笔", badgeClass: "foreshadow", status: "遗落", statusClass: "lost", chapter: "第6章 · 断桥遗迹", characters: "", suggestChapter: "", detailRows: [{ label: "遗落说明", value: "主角经过断桥时看到石柱上的古老符文，但之后剧情未再提及。建议在后续章节补充呼应或标记为废弃" }] },
];

const WORLD_ITEMS = [
  { text: "这个世界存在三种灵力：金、木、水。灵力修炼者被称为「灵使」" },
  { text: "帝国历 1037 年，大陆分裂为七国，中央帝国名存实亡" },
  { text: "灵力等级划分：初灵 → 通灵 → 御灵 → 宗灵 → 圣灵，每级三阶" },
  { text: "金灵主攻伐，木灵主生机，水灵主变化。三者可相生相克" },
  { text: "「灵脉」是天地灵力汇聚之地，七国各据一条主脉" },
  { text: "禁忌之术「融灵」可融合不同灵力属性，但成功率不足万一" },
];

const WORLD_CARDS = [
  { name: "玄天宗宗门", category: "地理", catClass: "protagonist", tags: ["剑修发源地", "七峰十二堂", "护山大阵"], desc: "位于苍云山脉主峰，占地三百里。宗门分七峰十二堂，以剑道与符法闻名南疆。护山大阵每甲子重启一次，需七峰首座合力催动。", chapters: "1-23", lastUpdate: "第14章" },
  { name: "灵力体系", category: "体系", catClass: "ally", tags: ["九境体系", "五行灵力", "变异属性"], desc: "修炼分九境：凝气→筑基→开光→融合→心动→金丹→元婴→化神→渡劫。每境分前中后三期。灵力属性分金木水火土五行，变异属性有雷、冰、风、暗。", chapters: "3-21", lastUpdate: "第12章" },
  { name: "后山禁地", category: "地理", catClass: "opponent", tags: ["古老遗迹", "阵法封印", "剧情触发点"], desc: "宗门后山深处一处古老遗迹，被层层阵法封印。传闻每甲子阵眼松动，曾有弟子误入后再未归来。林霄在第12章听闻此禁地，引发后续剧情。", chapters: "12", lastUpdate: "第12章" },
];

const SECRET_ROWS: SecretRow[] = [
  { secret: "林夜是苏晚晴失散多年的弟弟", known: { "林夜": true, "苏晚晴": true, "叶灵": null, "青袍老者": true }, level: "partial", debt: 15 },
  { secret: "叶灵是反派派来的卧底", known: { "林夜": null, "苏晚晴": null, "叶灵": true, "青袍老者": true }, level: "absolute", debt: 35 },
  { secret: "天象核心是一把钥匙", known: { "林夜": true, "苏晚晴": null, "叶灵": null, "青袍老者": true }, level: "absolute", debt: 45 },
  { secret: "林夜的真实身世是帝国遗孤", known: { "林夜": true, "苏晚晴": true, "叶灵": true, "青袍老者": true }, level: "open", debt: "—" },
];

const SECRET_CHARACTERS = ["林夜", "苏晚晴", "叶灵", "青袍老者"];

const SIDEBAR_TABS: { id: DTab; icon: string; label: string; count: string }[] = [
  { id: "character", icon: "👥", label: "人物库", count: "18 人" },
  { id: "timeline", icon: "⏱️", label: "时间线库", count: "5 个节点" },
  { id: "commitments", icon: "📖", label: "剧情承诺库", count: '12 活跃 · 3 待回收' },
  { id: "world", icon: "🌍", label: "世界观库", count: "9 项" },
  { id: "secrets", icon: "🔐", label: "秘密矩阵", count: '4 活跃 · 2 不对称' },
];

const FORESHADOW_FILTER_BTNS: { key: ForeshadowFilter; label: string }[] = [
  { key: "all", label: "全部 (31)" },
  { key: "active", label: "活跃 (12)" },
  { key: "pending", label: "待回收 (3)" },
  { key: "recovered", label: "已回收 (15)" },
  { key: "lost", label: "遗落 (1)" },
];

const WORLD_FILTER_BTNS: { key: WorldFilter; label: string }[] = [
  { key: "all", label: "全部 (9)" },
  { key: "geography", label: "地理 (3)" },
  { key: "history", label: "历史 (2)" },
  { key: "magic", label: "体系 (2)" },
  { key: "faction", label: "势力 (2)" },
];

const SECRETS_FILTER_BTNS: { key: SecretsFilter; label: string }[] = [
  { key: "all", label: "全部 (4)" },
  { key: "absolute", label: "绝对秘密 (2)" },
  { key: "partial", label: "部分公开 (1)" },
  { key: "open", label: "已公开 (1)" },
];

const MOBILE_CHARACTERS = [
  { name: "苏铭", avatarVariant: "v1", avatarChar: "苏", tags: ["主角", "坚韧", "重情义", "天赋异禀"], traits: ["坚韧", "重情义", "天赋异禀"], desc: "出身平凡村庄的少年，体内蕴藏着未被觉醒的灵力。性格坚韧不屈，对身边之人极为珍视。在灵力觉醒后踏上修行之路，逐渐发现自己与星穹之间的隐秘联系。" },
  { name: "叶青寒", avatarVariant: "v2", avatarChar: "叶", tags: ["盟友", "冷傲", "剑术天才", "神秘身世"], traits: ["冷傲", "剑术天才", "神秘身世"], desc: "玄天宗内门弟子，剑术造诣远超同辈。性格孤傲冷淡，实则内心有着不为人知的柔软。身世成谜，似乎与某个没落的世家有关。" },
  { name: "夜无痕", avatarVariant: "v3", avatarChar: "夜", tags: ["对手", "亦正亦邪", "实力深不可测"], traits: ["亦正亦邪", "实力深不可测"], desc: "来历不明的神秘修行者，行事无章可循。时而相助，时而对立，令人难以捉摸。其实力远超表面所见，似乎在暗中推动着某些事件的发展。" },
];

const MOBILE_TIMELINE = [
  { day: "第 1 天", title: "主角觉醒灵力", desc: "苏铭在村庄后山的古井旁意外觉醒灵力，引发了一场小型灵力风暴。村中长者意识到这个少年的不凡之处。", className: "" },
  { day: "第 3 天", title: "离开村庄前往王城", desc: "在村长的指引下，苏铭告别故乡，踏上前往王城的路途。临行前获赠一枚神秘玉佩。", className: "" },
  { day: "第 7 天", title: "抵达王城，初遇考核使", desc: "历经波折抵达王城，恰逢玄天宗三年一度的宗门考核。叶青寒作为考核使首次登场。", className: "" },
  { day: "第 15 天", title: "宗门考核，进入秘境", desc: "宗门考核进入关键阶段——秘境试炼。苏铭与众多考生一同踏入未知空间，面对前所未有的挑战。", className: "current" },
  { day: "第 20 天", title: "考核结束", desc: "秘境试炼结束，考核结果揭晓。各考生命运将走向何方…（未写）", className: "future" },
];

const MOBILE_PLOT_ITEMS = [
  { title: "神秘玉佩", type: "pending", chapter: "第3章埋设", suggest: "建议回收：第15-20章", desc: "苏铭离开村庄时获赠的神秘玉佩，蕴含着未知力量。村长称其为\"故人所托\"，暗示玉佩与苏铭的身世有关。" },
  { title: "禁术残卷", type: "pending", chapter: "第7章埋设", suggest: "建议回收：第18-22章", desc: "苏铭在王城旧书店中意外发现的残破卷轴，记载着一种被明令禁止的古老术法。残卷仅存三分之一，其余部分下落不明。" },
  { title: "王城地下的异响", type: "pending", chapter: "第10章埋设", suggest: "建议回收：第20-25章", desc: "多名王城居民反映深夜地下传来异响，玄天宗派人调查却毫无发现。异响出现的规律似乎与月相有关。" },
  { title: "客栈密语", type: "done", chapter: "第8章已回收", suggest: "", desc: "苏铭在客栈中偷听到的神秘对话，指向了玄天宗内部的一股暗流。此线索在第8章帮助他识破了考核中的一次暗算。" },
  { title: "村长的异常", type: "done", chapter: "第5章已回收", suggest: "", desc: "村长在苏铭觉醒灵力后的异常反应暗示他早已知晓一切。此伏笔在第5章得到回收——村长揭示了与苏铭父亲的旧日约定。" },
];

const MOBILE_WORLD_CARDS = [
  { name: "玄天宗", cat: "geo", icon: "🏛", iconClass: "geo", desc: "天下第一宗门，坐落于天玄山脉之巅，占据三条主灵脉交汇之处。" },
  { name: "灵力体系", cat: "sys", icon: "⚙", iconClass: "sys", desc: "九境：凝气→筑基→开脉→通玄→化神→归真→合道→造化→破天。" },
  { name: "后山禁地", cat: "geo", icon: "⛰", iconClass: "geo", desc: "玄天宗后山被列为禁地的古老遗迹，据传是上古大能的陨落之所。" },
  { name: "七国局势", cat: "his", icon: "📖", iconClass: "his", desc: "天下七国割据百年，表面和平之下暗流涌动，各国均暗中蓄力。" },
  { name: "融灵禁术", cat: "sys", icon: "⚃", iconClass: "sys", desc: "以极端手段融合不同属性灵力的禁忌之术，修炼者九死一生。" },
  { name: "灵脉分布", cat: "geo", icon: "🌌", iconClass: "geo", desc: "天下九条主灵脉贯穿大陆，灵脉节点处皆建有重镇或宗门。" },
];

// ── Helpers ──

const SEARCH_PLACEHOLDER = "搜索人物、时间线、剧情承诺、世界观…";

function getFactionLabel(faction: string): string {
  const map: Record<string, string> = { protagonist: "主角", ally: "盟友", neutral: "中立", opponent: "对手", villain: "反派" };
  return map[faction] || faction;
}

const STATUS_META_MAP: Record<string, { icon: string; completed: string; recovered: string }> = {
  "pending": { icon: "⚠", completed: "", recovered: "" },
  "active": { icon: "", completed: "第8章回收", recovered: "" },
  "recovered": { icon: "", completed: "", recovered: "第5章回收" },
};

// ── Page Component ──

export default function VaultsPage() {
  const params = useParams();
  const router = useRouter();
  const { isLoading: authLoading, isAuthenticated } = useAuth();

  const projectId = params.projectId as string;

  // Desktop states
  const [activeTab, setActiveTab] = useState<DTab>("character");
  const [charFilter, setCharFilter] = useState<CharFilter>("all");
  const [foreshadowFilter, setForeshadowFilter] = useState<ForeshadowFilter>("all");
  const [worldFilter, setWorldFilter] = useState<WorldFilter>("all");
  const [secretsFilter, setSecretsFilter] = useState<SecretsFilter>("all");
  const [expandedForeshadow, setExpandedForeshadow] = useState<string | null>(null);
  const [collapsedSections, setCollapsedSections] = useState<Set<string>>(new Set());
  const [selectedCharacterName, setSelectedCharacterName] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");

  // Mobile states
  const [mobileTab, setMobileTab] = useState(0);
  const [expandedCharCards, setExpandedCharCards] = useState<Set<number>>(new Set());
  const [expandedPlotCards, setExpandedPlotCards] = useState<Set<number>>(new Set());
  const [mobilePlotFilter, setMobilePlotFilter] = useState<MobilePlotFilter>("all");
  const [mobileWorldFilter, setMobileWorldFilter] = useState<WorldCatFilter>("all");
  const [mobileSearchQuery, setMobileSearchQuery] = useState("");

  // Auth check
  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.push("/auth");
    }
  }, [authLoading, isAuthenticated, router]);

  // Load vault data
  const [vaultData, setVaultData] = useState<{
    characters: VaultCharacter[];
    timelines: VaultTimeline[];
    plotPromises: VaultPlotPromise[];
    worlds: VaultWorld[];
  } | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);

  useEffect(() => {
    if (!projectId || !isAuthenticated) return;

    const loadVaultData = async () => {
      try {
        setIsLoading(true);
        setLoadError(null);
        const [charsRes, tlRes, ppRes, wldRes] = await Promise.all([
          vaultApi.getCharacters(projectId),
          vaultApi.getTimeline(projectId),
          vaultApi.getPlotPromises(projectId),
          vaultApi.getWorld(projectId),
        ]);
        
        setVaultData({
          characters: safeArray<VaultCharacter>(charsRes.data, []),
          timelines: safeArray<VaultTimeline>(tlRes.data, []),
          plotPromises: safeArray<VaultPlotPromise>(ppRes.data, []),
          worlds: safeArray<VaultWorld>(wldRes.data, []),
        });
      } catch (error) {
        console.error("Failed to load vault data:", error);
        setLoadError(error instanceof Error ? error.message : "加载知识库数据失败");
        setVaultData(null);
      } finally {
        setIsLoading(false);
      }
    };

    loadVaultData();
  }, [projectId, isAuthenticated]);

  // ── API-driven data transformations ──
  // VaultCharacter → desktop card format
  const apiCharacterCards = useMemo(() => {
    if (!vaultData) return CHARACTER_CARDS;
    const roleFactionMap: Record<string, string> = {
      "主角": "protagonist", "protagonist": "protagonist",
      "盟友": "ally", "ally": "ally",
      "中立": "neutral", "neutral": "neutral",
      "对手": "opponent", "opponent": "opponent",
      "反派": "villain", "villain": "villain",
    };
    const getFaction = (role: string): string => roleFactionMap[role.toLowerCase()] || "neutral";
    const getStatusDotColor = (faction: string): string => {
      const colorMap: Record<string, string> = {
        protagonist: "var(--color-success)",
        ally: "var(--color-success)",
        neutral: "var(--color-warning)",
        opponent: "var(--color-warning)",
        villain: "var(--color-danger)",
      };
      return colorMap[faction] || "var(--color-text-secondary)";
    };
    return vaultData.characters.map((c) => ({
      name: c.name,
      faction: getFaction(c.role),
      avatarClass: getFaction(c.role),
      avatarChar: c.name.charAt(0),
      chapters: "—",
      tags: c.traits && c.traits.length > 0 ? c.traits : [c.role],
      status: c.description ? c.description.slice(0, 20) + (c.description.length > 20 ? "…" : "") : "—",
      statusDotColor: getStatusDotColor(getFaction(c.role)),
    }));
  }, [vaultData]);

  // VaultCharacter → detail modal format
  const apiCharacterDetails = useMemo(() => {
    if (!vaultData) return CHARACTER_DETAILS;
    const details: Record<string, CharacterDetail> = {};
    vaultData.characters.forEach((c) => {
      details[c.name] = {
        name: c.name,
        faction: c.role,
        background: c.background || "暂无背景信息",
        ability: c.knowledge || "暂无能力信息",
        relationships: c.relationships?.map((r) => `${r.relationship}: ${r.description}`).join(" · ") || "暂无关联信息",
        arc: c.arc || "暂无成长弧线",
      };
    });
    return details;
  }, [vaultData]);

  // VaultTimeline → timeline events
  const apiTimelineEvents = useMemo(() => {
    if (!vaultData || vaultData.timelines.length === 0) return TIMELINE_EVENTS;
    return vaultData.timelines.map((tl, idx) => ({
      day: tl.day !== undefined ? `第 ${tl.day} 天` : `事件 ${idx + 1}`,
      text: tl.description || tl.title || "未命名事件",
      className: idx === 0 ? "completed" : idx === vaultData.timelines.length - 1 ? "current" : "completed",
      isCurrent: idx === vaultData.timelines.length - 1,
    }));
  }, [vaultData]);

  // VaultTimeline → scene list
  const apiSceneList = useMemo(() => {
    if (!vaultData) return SCENE_LIST;
    const scenes: Array<{ chapter: string; summary: string }> = [];
    vaultData.timelines.forEach((tl) => {
      tl.events?.forEach((evt, idx) => {
        scenes.push({
          chapter: `Ch.${evt.chapter_number}`,
          summary: evt.event || tl.title || `事件 ${idx + 1}`,
        });
      });
    });
    return scenes.length > 0 ? scenes : SCENE_LIST;
  }, [vaultData]);

  // VaultPlotPromise → ForeshadowItem format
  const apiForeshadowItems = useMemo(() => {
    if (!vaultData) return FORESHADOW_ITEMS;
    const urgencyMap: Record<string, "high" | "medium" | "low"> = {
      "高": "high", "high": "high",
      "中": "medium", "medium": "medium",
      "低": "low", "low": "low",
    };
    const getBadgeClass = (s: string): string => {
      if (s === "fulfilled") return "wrap";
      if (s === "broken") return "lost";
      if (s === "pending") return "foreshadow";
      return "advance";
    };
    const statusLabel: Record<string, string> = {
      pending: "待回收",
      fulfilled: "已回收",
      broken: "遗落",
    };
    const statusClass: Record<string, string> = {
      pending: "pending",
      fulfilled: "recovered",
      broken: "lost",
    };
    return vaultData.plotPromises.map((pp) => ({
      id: pp.id,
      title: pp.title || pp.description.slice(0, 30),
      urgency: (urgencyMap[pp.urgency?.toLowerCase() || ""] || "medium") as "high" | "medium" | "low",
      badge: pp.type || "伏笔",
      badgeClass: getBadgeClass(pp.status),
      status: statusLabel[pp.status] || pp.status,
      statusClass: statusClass[pp.status] || "pending",
      chapter: `第${pp.introduced_at}章`,
      characters: "",
      suggestChapter: pp.resolved_at ? `已解决于第${pp.resolved_at}章` : "",
      detailRows: [{ label: "描述", value: pp.description }],
    }));
  }, [vaultData]);

  // VaultWorld → world items (text list)
  const apiWorldItems = useMemo(() => {
    if (!vaultData) return WORLD_ITEMS;
    return vaultData.worlds.map((w) => ({
      text: `${w.name}（${w.category}）：${w.description}`,
    }));
  }, [vaultData]);

  // VaultWorld → world cards
  const apiWorldCards = useMemo(() => {
    if (!vaultData) return WORLD_CARDS;
    const catClassMap: Record<string, string> = {
      地理: "protagonist", geography: "protagonist",
      体系: "ally", system: "ally",
      历史: "opponent", history: "opponent",
      势力: "neutral", faction: "neutral",
    };
    return vaultData.worlds.map((w) => ({
      name: w.name,
      category: w.category,
      catClass: catClassMap[w.category?.toLowerCase()] || "ally",
      tags: w.rules || [],
      desc: w.description,
      chapters: w.source_chapter ? `第${w.source_chapter}章` : "—",
      lastUpdate: w.source_chapter ? `第${w.source_chapter}章` : "—",
    }));
  }, [vaultData]);

  // Dynamic filter buttons with counts
  const apiCharFilterLabels = useMemo(() => {
    if (!vaultData) return CHAR_FILTER_LABELS;
    const counts: Record<string, number> = { all: vaultData.characters.length, protagonist: 0, ally: 0, neutral: 0, opponent: 0, villain: 0 };
    vaultData.characters.forEach((c) => {
      const roleLower = c.role?.toLowerCase() || "";
      if (["主角", "protagonist"].includes(roleLower)) counts.protagonist++;
      else if (["盟友", "ally"].includes(roleLower)) counts.ally++;
      else if (["中立", "neutral"].includes(roleLower)) counts.neutral++;
      else if (["对手", "opponent"].includes(roleLower)) counts.opponent++;
      else if (["反派", "villain"].includes(roleLower)) counts.villain++;
      else counts.neutral++;
    });
    return [
      { key: "all" as CharFilter, label: `全部 (${counts.all})` },
      { key: "protagonist" as CharFilter, label: `主角 (${counts.protagonist})` },
      { key: "ally" as CharFilter, label: `盟友 (${counts.ally})` },
      { key: "neutral" as CharFilter, label: `中立 (${counts.neutral})` },
      { key: "opponent" as CharFilter, label: `对手 (${counts.opponent})` },
      { key: "villain" as CharFilter, label: `反派 (${counts.villain})` },
    ];
  }, [vaultData]);

  const apiForeshadowFilterBtns = useMemo(() => {
    if (!vaultData) return FORESHADOW_FILTER_BTNS;
    const counts = { all: vaultData.plotPromises.length, active: 0, pending: 0, recovered: 0, lost: 0 };
    vaultData.plotPromises.forEach((pp) => {
      if (pp.status === "pending") { counts.pending++; counts.active++; }
      else if (pp.status === "fulfilled") { counts.recovered++; }
      else if (pp.status === "broken") { counts.lost++; }
    });
    return [
      { key: "all" as ForeshadowFilter, label: `全部 (${counts.all})` },
      { key: "active" as ForeshadowFilter, label: `活跃 (${counts.active})` },
      { key: "pending" as ForeshadowFilter, label: `待回收 (${counts.pending})` },
      { key: "recovered" as ForeshadowFilter, label: `已回收 (${counts.recovered})` },
      { key: "lost" as ForeshadowFilter, label: `遗落 (${counts.lost})` },
    ];
  }, [vaultData]);

  const apiWorldFilterBtns = useMemo(() => {
    if (!vaultData) return WORLD_FILTER_BTNS;
    const catCounts: Record<string, number> = {};
    vaultData.worlds.forEach((w) => {
      const cat = w.category?.toLowerCase() || "other";
      catCounts[cat] = (catCounts[cat] || 0) + 1;
    });
    const total = vaultData.worlds.length;
    return [
      { key: "all" as WorldFilter, label: `全部 (${total})` },
      { key: "geography" as WorldFilter, label: `地理 (${catCounts["geography"] || catCounts["地理"] || 0})` },
      { key: "history" as WorldFilter, label: `历史 (${catCounts["history"] || catCounts["历史"] || 0})` },
      { key: "magic" as WorldFilter, label: `体系 (${catCounts["magic"] || catCounts["体系"] || catCounts["system"] || 0})` },
      { key: "faction" as WorldFilter, label: `势力 (${catCounts["faction"] || catCounts["势力"] || 0})` },
    ];
  }, [vaultData]);

  // Derived active variables
  const activeCharCards = vaultData ? apiCharacterCards : CHARACTER_CARDS;
  const activeCharDetails = vaultData ? apiCharacterDetails : CHARACTER_DETAILS;
  const activeTimelineEvents = vaultData ? apiTimelineEvents : TIMELINE_EVENTS;
  const activeSceneList = vaultData ? apiSceneList : SCENE_LIST;
  const activeForeshadowItems = vaultData ? apiForeshadowItems : FORESHADOW_ITEMS;
  const activeWorldItems = vaultData ? apiWorldItems : WORLD_ITEMS;
  const activeWorldCards = vaultData ? apiWorldCards : WORLD_CARDS;
  const activeCharFilterLabels = vaultData ? apiCharFilterLabels : CHAR_FILTER_LABELS;
  const activeForeshadowFilterBtns = vaultData ? apiForeshadowFilterBtns : FORESHADOW_FILTER_BTNS;
  const activeWorldFilterBtns = vaultData ? apiWorldFilterBtns : WORLD_FILTER_BTNS;

  // Sidebar stats
  const apiSidebarTabs = useMemo(() => {
    if (!vaultData) return SIDEBAR_TABS;
    const activePP = vaultData.plotPromises.filter((p) => p.status === "pending").length;
    return [
      { id: "character" as DTab, icon: "👥", label: "人物库", count: `${vaultData.characters.length} 人` },
      { id: "timeline" as DTab, icon: "⏱️", label: "时间线库", count: `${vaultData.timelines.length} 个节点` },
      { id: "commitments" as DTab, icon: "📖", label: "剧情承诺库", count: `${activePP} 活跃 · ${vaultData.plotPromises.filter((p) => p.status === "fulfilled").length} 已回收` },
      { id: "world" as DTab, icon: "🌍", label: "世界观库", count: `${vaultData.worlds.length} 项` },
      { id: "secrets" as DTab, icon: "🔐", label: "秘密矩阵", count: `${SECRET_ROWS.length} 活跃` },
    ];
  }, [vaultData]);

  // Mobile data from API
  const apiMobileCharacters = useMemo(() => {
    if (!vaultData) return MOBILE_CHARACTERS;
    return vaultData.characters.map((c, i) => ({
      name: c.name,
      avatarVariant: `v${(i % 3) + 1}`,
      avatarChar: c.name.charAt(0),
      tags: c.role ? [c.role, ...(c.traits || []).slice(0, 3)] : (c.traits || []).slice(0, 4),
      traits: c.traits || [],
      desc: c.description || c.background || "暂无详细描述",
    }));
  }, [vaultData]);

  const apiMobileTimeline = useMemo(() => {
    if (!vaultData || vaultData.timelines.length === 0) return MOBILE_TIMELINE;
    return vaultData.timelines.map((tl, idx) => ({
      day: tl.day !== undefined ? `第 ${tl.day} 天` : `阶段 ${idx + 1}`,
      title: tl.title || "事件",
      desc: tl.description || "暂无描述",
      className: idx === vaultData.timelines.length - 1 ? "current" : "",
    }));
  }, [vaultData]);

  const apiMobilePlotItems = useMemo(() => {
    if (!vaultData) return MOBILE_PLOT_ITEMS;
    return vaultData.plotPromises.map((pp) => ({
      title: pp.title || pp.description.slice(0, 20),
      type: pp.status === "fulfilled" ? "done" as const : "pending" as const,
      chapter: `第${pp.introduced_at}章埋设`,
      suggest: pp.resolved_at ? `第${pp.resolved_at}章回收` : "待回收",
      desc: pp.description,
    }));
  }, [vaultData]);

  const apiMobileWorldCards = useMemo(() => {
    if (!vaultData) return MOBILE_WORLD_CARDS;
    const catIconMap: Record<string, { icon: string; iconClass: string }> = {
      地理: { icon: "🏛", iconClass: "geo" },
      geography: { icon: "🏛", iconClass: "geo" },
      体系: { icon: "⚙", iconClass: "sys" },
      system: { icon: "⚙", iconClass: "sys" },
      历史: { icon: "📖", iconClass: "his" },
      history: { icon: "📖", iconClass: "his" },
      势力: { icon: "🏴", iconClass: "power" },
      faction: { icon: "🏴", iconClass: "power" },
    };
    return vaultData.worlds.map((w) => {
      const cat = w.category?.toLowerCase() || "";
      const mapping = catIconMap[cat] || catIconMap[w.category] || { icon: "📌", iconClass: "sys" };
      return {
        name: w.name,
        cat: mapping.iconClass,
        icon: mapping.icon,
        iconClass: mapping.iconClass,
        desc: w.description,
      };
    });
  }, [vaultData]);

  // Final mobile data
  const activeMobileCharacters = vaultData ? apiMobileCharacters : MOBILE_CHARACTERS;
  const activeMobileTimeline = vaultData ? apiMobileTimeline : MOBILE_TIMELINE;
  const activeMobilePlotItems = vaultData ? apiMobilePlotItems : MOBILE_PLOT_ITEMS;
  const activeMobileWorldCards = vaultData ? apiMobileWorldCards : MOBILE_WORLD_CARDS;

  // Dynamic secrets filter counts
  const apiSecretsFilterBtns = useMemo(() => {
    if (!vaultData) return SECRETS_FILTER_BTNS;
    const absCount = SECRET_ROWS.filter((s) => s.level === "absolute").length;
    const partCount = SECRET_ROWS.filter((s) => s.level === "partial").length;
    const openCount = SECRET_ROWS.filter((s) => s.level === "open").length;
    return [
      { key: "all" as SecretsFilter, label: `全部 (${SECRET_ROWS.length})` },
      { key: "absolute" as SecretsFilter, label: `绝对秘密 (${absCount})` },
      { key: "partial" as SecretsFilter, label: `部分公开 (${partCount})` },
      { key: "open" as SecretsFilter, label: `已公开 (${openCount})` },
    ];
  }, [vaultData]);

  // Filtered data
  const filteredChars = useMemo(() => {
    if (charFilter === "all") return activeCharCards;
    return activeCharCards.filter(c => c.faction === charFilter);
  }, [charFilter, activeCharCards]);

  const filteredForeshadows = useMemo(() => {
    if (foreshadowFilter === "all") return activeForeshadowItems;
    return activeForeshadowItems.filter(f => f.statusClass === foreshadowFilter);
  }, [foreshadowFilter, activeForeshadowItems]);

  const filteredSecrets = useMemo(() => {
    if (secretsFilter === "all") return SECRET_ROWS;
    return SECRET_ROWS.filter(s => s.level === secretsFilter);
  }, [secretsFilter]);

  const filteredMobilePlot = useMemo(() => {
    if (mobilePlotFilter === "all") return activeMobilePlotItems;
    return activeMobilePlotItems.filter(p => p.type === mobilePlotFilter);
  }, [mobilePlotFilter, activeMobilePlotItems]);

  const filteredMobileWorld = useMemo(() => {
    if (mobileWorldFilter === "all") return activeMobileWorldCards;
    return activeMobileWorldCards.filter(c => c.cat === mobileWorldFilter);
  }, [mobileWorldFilter, activeMobileWorldCards]);

  const filteredMobileChars = useMemo(() => {
    if (!mobileSearchQuery.trim()) return activeMobileCharacters;
    const q = mobileSearchQuery.toLowerCase();
    return activeMobileCharacters.filter(c =>
      c.name.toLowerCase().includes(q) ||
      c.tags.some(t => t.toLowerCase().includes(q))
    );
  }, [mobileSearchQuery, activeMobileCharacters]);

  // Toggle section collapse
  const toggleSection = useCallback((sectionId: string) => {
    setCollapsedSections(prev => {
      const next = new Set(prev);
      if (next.has(sectionId)) next.delete(sectionId);
      else next.add(sectionId);
      return next;
    });
  }, []);

  // Toggle foreshadow expand
  const toggleForeshadow = useCallback((id: string) => {
    setExpandedForeshadow(prev => prev === id ? null : id);
  }, []);

  // Mobile toggle char card
  const toggleMobileChar = useCallback((index: number) => {
    setExpandedCharCards(prev => {
      const next = new Set(prev);
      if (next.has(index)) next.delete(index);
      else next.add(index);
      return next;
    });
  }, []);

  // Mobile toggle plot card
  const toggleMobilePlot = useCallback((index: number) => {
    setExpandedPlotCards(prev => {
      const next = new Set(prev);
      if (next.has(index)) next.delete(index);
      else next.add(index);
      return next;
    });
  }, []);

  // Get character detail
  const getCharDetail = useCallback((name: string): CharacterDetail | null => {
    return activeCharDetails[name] || null;
  }, [activeCharDetails]);

  // Keyboard shortcut
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        const input = document.getElementById("dGlobalSearch") as HTMLInputElement;
        if (input) input.focus();
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, []);

  if (authLoading) {
    return (
      <div className={styles.loading}>
        <Spinner />
      </div>
    );
  }

  // ── Render: Character Detail Modal ──
  const renderCharModal = () => {
    if (!selectedCharacterName) return null;
    const card = activeCharCards.find(c => c.name === selectedCharacterName);
    const detail = getCharDetail(selectedCharacterName);

    return (
      <div className={styles.dDetailOverlay} onClick={() => setSelectedCharacterName(null)}>
        <div className={styles.dDetailModal} onClick={(e) => e.stopPropagation()}>
          <div className={styles.dDetailModalHeader}>
            <span className={styles.dDetailModalTitle}>{selectedCharacterName}</span>
            <button className={styles.dDetailModalClose} onClick={() => setSelectedCharacterName(null)}>
              <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
                <path d="M3 3l8 8M11 3l-8 8" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
              </svg>
            </button>
          </div>
          <div className={styles.dDetailModalBody}>
            {detail ? (
              <>
                <div className={styles.dDetailField}>
                  <div className={styles.dDetailFieldLabel}>背景</div>
                  <div className={styles.dDetailFieldValue}>{detail.background}</div>
                </div>
                <div className={styles.dDetailField}>
                  <div className={styles.dDetailFieldLabel}>能力</div>
                  <div className={styles.dDetailFieldValue}>{detail.ability.split('\n').map((l, i) => <span key={i}>{l}<br /></span>)}</div>
                </div>
                <div className={styles.dDetailField}>
                  <div className={styles.dDetailFieldLabel}>人物关系</div>
                  <div className={styles.dDetailFieldValue}>{detail.relationships}</div>
                </div>
                <div className={styles.dDetailField}>
                  <div className={styles.dDetailFieldLabel}>角色弧线</div>
                  <div className={styles.dDetailFieldValueMono}>{detail.arc}</div>
                </div>
              </>
            ) : (
              <>
                <div className={styles.dDetailField}>
                  <div className={styles.dDetailFieldLabel}>阵营</div>
                  <div className={styles.dDetailFieldValue}>{card ? getFactionLabel(card.faction) : "—"}</div>
                </div>
                <div className={styles.dDetailField}>
                  <div className={styles.dDetailFieldLabel}>当前状态</div>
                  <div className={styles.dDetailFieldValue}>{card?.status || "—"}</div>
                </div>
                <div className={styles.dDetailField}>
                  <div className={styles.dDetailFieldLabel}>出场 {card?.chapters || "?"} 章</div>
                  <div className={styles.dDetailFieldValueItalic}>详细档案待完善</div>
                </div>
              </>
            )}
          </div>
        </div>
      </div>
    );
  };

  // ── Render: Desktop Search Box ──
  const dSearchBox = (
    <div className={styles.dSearchBox}>
      <svg width="14" height="14" viewBox="0 0 16 16" fill="none">
        <circle cx="7" cy="7" r="4.5" stroke="currentColor" strokeWidth="1.5" />
        <path d="M10.5 10.5L14 14" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
      </svg>
      <input
        id="dGlobalSearch"
        type="text"
        placeholder={SEARCH_PLACEHOLDER}
        value={searchQuery}
        onChange={(e) => setSearchQuery(e.target.value)}
        className={styles.dSearchInput}
      />
      <span className={styles.dSearchShortcut}>⌘K</span>
    </div>
  );

  // ── Render: Desktop Sidebar Stats ──
  const dSidebarStats = (
    <div className={styles.dSidebarStats}>
      <div className={styles.dSidebarStatRow}>
        <span className={styles.dStatLabel}>总字数</span>
        <span className={styles.dStatValue}>124,800</span>
      </div>
      <div className={styles.dSidebarStatRow}>
        <span className={styles.dStatLabel}>已完成章节</span>
        <span className={styles.dStatValue}>23 / 40</span>
      </div>
      <div className={styles.dSidebarStatRow}>
        <span className={styles.dStatLabel}>承诺回收率</span>
        <span className={styles.dStatValue}>78.9%</span>
      </div>
      <div className={styles.dSidebarStatRow} style={{ color: "var(--color-warning)" }}>
        <span className={styles.dStatLabel}>🏥 健康告警</span>
        <span className={styles.dStatValue}>2</span>
      </div>
      <div className={styles.dSidebarStatRow}>
        <span className={styles.dStatLabel}>🔐 活跃秘密</span>
        <span className={styles.dStatValue}>4</span>
      </div>
      <div className={styles.dSidebarStatRow}>
        <span className={styles.dStatLabel}>最后同步</span>
        <span className={styles.dStatValue}>2 分钟前</span>
      </div>
    </div>
  );

  // ── Render: Character Panel ──
  const dCharacterPanel = (
    <div className={`${styles.dContentPanel} ${activeTab === "character" ? styles.active : ""}`}>
      <div className={styles.dFilterBar}>
        {activeCharFilterLabels.map((btn) => (
          <button
            key={btn.key}
            className={`${styles.dFilterBtn} ${charFilter === btn.key ? styles.active : ""}`}
            onClick={() => setCharFilter(btn.key)}
          >
            {btn.label}
          </button>
        ))}
      </div>
      <div className={styles.dCharacterGrid}>
        {(() => {
          const searchedCharacters = searchQuery
            ? filteredChars.filter(c => c.name.includes(searchQuery))
            : filteredChars;
          return searchedCharacters.map((char) => (
          <div
            key={char.name}
            className={styles.dCharacterCard}
            data-faction={char.faction}
            onClick={() => setSelectedCharacterName(char.name)}
          >
            <div className={styles.dCharacterChapters}>出场 {char.chapters} 章</div>
            <div className={styles.dCharacterCardTop}>
              <div className={`${styles.dCharacterAvatar} ${styles[char.avatarClass]}`}>{char.avatarChar}</div>
              <div className={styles.dCharacterInfo}>
                <div className={styles.dCharacterName}>{char.name}</div>
                <span className={`${styles.dCharacterFaction} ${styles[char.faction]}`}>{getFactionLabel(char.faction)}</span>
              </div>
            </div>
            <div className={styles.dCharacterTags}>
              {char.tags.map((tag) => (
                <span key={tag} className={styles.dCharacterTag}>{tag}</span>
              ))}
            </div>
            <div className={styles.dCharacterStatus}>
              <span className={styles.dCharacterStatusDot} style={{ background: char.statusDotColor }}></span>
              {char.status}
            </div>
          </div>
        ))}
        )()}
        <button className={styles.dAddCharacterBtn} onClick={async () => {
  const name = window.prompt("请输入角色名称：");
  if (!name || !name.trim()) return;
  showToast("info", `添加角色「${name.trim()}」功能待对接后端`);
}}>
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
            <path d="M8 3v10M3 8h10" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
          </svg>
          添加角色
        </button>
      </div>
    </div>
  );

  // ── Render: Timeline Panel ──
  const dTimelinePanel = (
    <div className={`${styles.dContentPanel} ${activeTab === "timeline" ? styles.active : ""}`}>
      <section className={styles.dMemorySection}>
        <div className={`${styles.dSectionCard} ${collapsedSections.has("timeline") ? styles.collapsed : ""}`} id="dCard-timeline">
          <div className={styles.dSectionCardHeader} onClick={() => toggleSection("timeline")}>
            <div className={styles.dSectionCardTitle}>
              <span className={styles.dCardIcon} style={{ background: "rgba(52,211,153,0.1)", color: "var(--color-success)" }}>⏳</span>
              时间线
              <span className={styles.dSectionCardCount}>5 个节点</span>
            </div>
            <div className={styles.dSectionCardToggle}>
              <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
                <path d="M3.5 5.25L7 8.75l3.5-3.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            </div>
          </div>
          <div className={styles.dSectionCardBody}>
            <div className={styles.dTimeline}>
              {activeTimelineEvents.map((evt, i) => (
                <div key={i} className={`${styles.dTimelineItem} ${evt.isCurrent ? styles.current : ""} ${evt.className === "completed" ? styles.completed : ""}`}>
                  <div className={styles.dTimelineDot}></div>
                  <div className={styles.dTimelineLabel}>{evt.day}</div>
                  <div className={styles.dTimelineText}>{evt.text}</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      <section className={styles.dMemorySection}>
        <div className={`${styles.dSectionCard} ${collapsedSections.has("scenes") ? styles.collapsed : ""}`} id="dCard-scenes">
          <div className={styles.dSectionCardHeader} onClick={() => toggleSection("scenes")}>
            <div className={styles.dSectionCardTitle}>
              <span className={styles.dCardIcon} style={{ background: "rgba(212,168,67,0.1)", color: "var(--color-brand-amber)" }}>🎬</span>
              场景摘要
              <span className={styles.dSectionCardCount}>12 个场景</span>
            </div>
            <div className={styles.dSectionCardToggle}>
              <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
                <path d="M3.5 5.25L7 8.75l3.5-3.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            </div>
          </div>
          <div className={styles.dSectionCardBody}>
            {activeSceneList.map((scene, i) => (
              <div key={i} className={styles.dSceneListItem}>
                <span className={styles.dSceneChapter}>{scene.chapter}</span>
                <span className={styles.dSceneSummary}>{scene.summary}</span>
              </div>
            ))}
          </div>
        </div>
      </section>
    </div>
  );

  // ── Render: Commitments Panel ──
  const dCommitmentsPanel = (
    <div className={`${styles.dContentPanel} ${activeTab === "commitments" ? styles.active : ""}`}>
      <div className={styles.dFilterBar}>
        {activeForeshadowFilterBtns.map((btn) => (
          <button
            key={btn.key}
            className={`${styles.dFilterBtn} ${foreshadowFilter === btn.key ? styles.active : ""}`}
            onClick={() => setForeshadowFilter(btn.key)}
          >
            {btn.label}
          </button>
        ))}
      </div>
      <div className={styles.dForeshadowList}>
        {filteredForeshadows.map((item) => (
          <div
            key={item.id}
            className={`${styles.dForeshadowCard} ${styles[`status${item.statusClass.charAt(0).toUpperCase() + item.statusClass.slice(1)}`]} ${expandedForeshadow === item.id ? styles.expanded : ""}`}
            data-status={item.statusClass}
            onClick={() => toggleForeshadow(item.id)}
          >
            <div className={styles.dForeshadowCardHeader}>
              <div className={styles.dForeshadowCardLeft}>
                <span className={`${styles.dUrgencyDot} ${styles[item.urgency]}`}></span>
                <span className={styles.dForeshadowTitle}>{item.title}</span>
                <span className={`${styles.dEventBadge} ${styles[item.badgeClass]}`}>{item.badge}</span>
              </div>
              <span className={`${styles.dStatusBadge} ${styles[item.statusClass]}`}>{item.status}</span>
            </div>
            <div className={styles.dForeshadowCardMeta}>
              <span className={styles.dMetaItem}>
                <svg width="12" height="12" viewBox="0 0 16 16" fill="none">
                  <path d="M2 4h12M4 4V3a1 1 0 011-1h6a1 1 0 011 1v1M5 7v4M8 7v4M11 7v4M3 4l1 9a1 1 0 001 1h6a1 1 0 001-1l1-9" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" />
                </svg>
                {item.chapter}
              </span>
              {item.characters && (
                <span className={styles.dMetaItem}>
                  <svg width="12" height="12" viewBox="0 0 16 16" fill="none">
                    <circle cx="8" cy="8" r="6" stroke="currentColor" strokeWidth="1.2" />
                    <circle cx="8" cy="6" r="2" stroke="currentColor" strokeWidth="1.2" />
                    <path d="M8 10v2" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" />
                  </svg>
                  {item.characters}
                </span>
              )}
              {item.suggestChapter && (
                <span className={styles.dMetaItem}>
                  <svg width="12" height="12" viewBox="0 0 16 16" fill="none">
                    <rect x="2" y="3" width="12" height="10" rx="1.5" stroke="currentColor" strokeWidth="1.2" />
                    <path d="M5 3V2M11 3V2M2 7h12" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" />
                  </svg>
                  {item.suggestChapter}
                </span>
              )}
            </div>
            <div className={styles.dForeshadowCardDetail}>
              {item.detailRows.slice(0, 1).map((row, i) => (
                <div key={i} className={styles.dDetailRow}>
                  <div className={styles.dDetailCol}>
                    <div className={styles.dDetailLabel}>{row.label}</div>
                    <div className={styles.dDetailValue}>{row.value}</div>
                  </div>
                </div>
              ))}
              {item.detailRows.length > 1 && (
                <div className={styles.dDetailRow}>
                  {item.detailRows.slice(1).map((row, i) => (
                    <div key={i} className={styles.dDetailCol}>
                      <div className={styles.dDetailLabel}>{row.label}</div>
                      <div className={styles.dDetailValue}>{row.value}</div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );

  // ── Render: World Panel ──
  const dWorldPanel = (
    <div className={`${styles.dContentPanel} ${activeTab === "world" ? styles.active : ""}`}>
      <div className={styles.dFilterBar}>
        {activeWorldFilterBtns.map((btn) => (
          <button
            key={btn.key}
            className={`${styles.dFilterBtn} ${worldFilter === btn.key ? styles.active : ""}`}
            onClick={() => setWorldFilter(btn.key)}
          >
            {btn.label}
          </button>
        ))}
      </div>
      <section className={styles.dMemorySection}>
        <div className={`${styles.dSectionCard} ${collapsedSections.has("worldview") ? styles.collapsed : ""}`} id="dCard-worldview">
          <div className={styles.dSectionCardHeader} onClick={() => toggleSection("worldview")}>
            <div className={styles.dSectionCardTitle}>
              <span className={styles.dCardIcon} style={{ background: "rgba(99,102,241,0.1)", color: "var(--color-brand-indigo)" }}>🌐</span>
              世界观设定
              <span className={styles.dSectionCardCount}>6 项</span>
            </div>
            <div className={styles.dSectionCardToggle}>
              <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
                <path d="M3.5 5.25L7 8.75l3.5-3.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            </div>
          </div>
          <div className={styles.dSectionCardBody}>
            {activeWorldItems.map((item, i) => (
              <div key={i} className={styles.dMemoryItem}>
                <span className={styles.dMemoryItemText}>{item.text}</span>
                <div className={styles.dMemoryItemActions}>
                  <button className={styles.dActionBtn} title="编辑" onClick={(e) => { e.stopPropagation(); showToast("info", "编辑功能即将上线"); }}>✏️</button>
                  <button className={`${styles.dActionBtn} ${styles.danger}`} title="删除" onClick={(e) => { e.stopPropagation(); showToast("info", "删除功能即将上线"); }}>🗑</button>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>
      <div className={styles.dWorldGrid}>
        {activeWorldCards.map((card, i) => (
          <div key={i} className={styles.dWorldCardStyle}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "var(--space-2)" }}>
              <span className={styles.dWorldCardName}>{card.name}</span>
              <span className={`${styles.dCharacterFaction} ${styles[card.catClass]}`} style={{ fontSize: "10px", padding: "1px 6px" }}>{card.category}</span>
            </div>
            <p className={styles.dWorldCardDesc}>{card.desc}</p>
            <div className={styles.dWorldCardTags}>
              {card.tags.map((tag) => (
                <span key={tag} className={styles.dCharacterTag}>{tag}</span>
              ))}
            </div>
            <div className={styles.dWorldCardChapter}>关联章节: {card.chapters} · 最后更新: {card.lastUpdate}</div>
          </div>
        ))}
      </div>
    </div>
  );

  // ── Render: Secrets Panel ──
  const dSecretsPanel = (
    <div className={`${styles.dContentPanel} ${activeTab === "secrets" ? styles.active : ""}`}>
      <div className={styles.dFilterBar}>
        {apiSecretsFilterBtns.map((btn) => (
          <button
            key={btn.key}
            className={`${styles.dFilterBtn} ${secretsFilter === btn.key ? styles.active : ""}`}
            onClick={() => setSecretsFilter(btn.key)}
          >
            {btn.label}
          </button>
        ))}
      </div>
      <section className={styles.dMemorySection}>
        <div className={`${styles.dSectionCard} ${collapsedSections.has("secrets-overview") ? styles.collapsed : ""}`} id="dCard-secrets-overview">
          <div className={styles.dSectionCardHeader} onClick={() => toggleSection("secrets-overview")}>
            <div className={styles.dSectionCardTitle}>
              <span className={styles.dCardIcon} style={{ background: "rgba(239,68,68,0.1)", color: "#ef4444" }}>🔐</span>
              信息不对称矩阵
              <span className={styles.dSectionCardCount}>角色知识状态</span>
            </div>
            <div className={styles.dSectionCardToggle}>
              <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
                <path d="M3.5 5.25L7 8.75l3.5-3.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            </div>
          </div>
          <div className={styles.dSectionCardBody}>
            <div className={styles.dSecretsTable}>
              <table className={styles.dSecretsTableEl}>
                <thead>
                  <tr className={styles.dSecretsTableHeadRow}>
                    <th className={styles.dSecretsTh}>秘密</th>
                    {SECRET_CHARACTERS.map((ch) => (
                      <th key={ch} className={styles.dSecretsTh}>{ch}</th>
                    ))}
                    <th className={styles.dSecretsTh}>层级</th>
                    <th className={styles.dSecretsTh}>债务</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredSecrets.map((row, i) => (
                    <tr key={i} className={styles.dSecretsTableRow}>
                      <td className={styles.dSecretsTd} style={{ fontWeight: 500 }}>{row.secret}</td>
                      {SECRET_CHARACTERS.map((ch) => {
                        const val = row.known[ch];
                        return (
                          <td key={ch} className={styles.dSecretsTd}>
                            {val === true ? <span className={styles.dSecretKnown}>✓ 知</span> :
                             val === false ? <span className={styles.dSecretNotKnown}>✗</span> :
                             <span className={styles.dSecretUnknown}>?</span>}
                          </td>
                        );
                      })}
                      <td className={styles.dSecretsTd}>
                        <span className={`${styles.dSecretLevelBadge} ${styles[row.level]}`}>{row.level === "open" ? "已公开" : row.level === "partial" ? "部分公开" : "绝对秘密"}</span>
                      </td>
                      <td className={styles.dSecretsTd}>
                        <span className={row.debt !== "—" && (row.debt as number) > 30 ? styles.dSecretDebtHigh : row.debt !== "—" ? styles.dSecretDebtMedium : styles.dSecretDebtNone}>
                          {row.debt}{row.debt !== "—" && (row.debt as number) > 30 ? " ⚠️" : ""}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className={styles.dSecretPanelGrid}>
              <div className={styles.dSecretDebtPanel}>
                <div className={styles.dSecretPanelTitle}>📊 秘密债务总览</div>
                <div className={styles.dSecretDebtAvg}>平均债务: 24</div>
                {SECRET_ROWS.filter(s => s.debt !== "—").map((s, i) => (
                  <div key={i} className={styles.dSecretDebtItem}>
                    <div className={styles.dSecretDebtItemLabel}>
                      <span>{s.secret}</span>
                      <span className={(s.debt as number) > 30 ? styles.dSecretDebtHigh : styles.dSecretDebtMedium}>{s.debt}</span>
                    </div>
                    <div className={styles.dProgressTrack}>
                      <div
                        className={styles.dProgressFill}
                        style={{ width: `${Math.min((s.debt as number) / 50 * 100, 100)}%`, background: (s.debt as number) > 30 ? "linear-gradient(90deg,#f59e0b,#ef4444)" : "#f59e0b" }}
                      ></div>
                    </div>
                  </div>
                ))}
                <div className={styles.dSecretDebtFormula}>债务 = (当前章 - 埋设章) × 未知角色数 · 阈值 30 建议揭露</div>
              </div>
              <div className={styles.dSecretHealthPanel}>
                <div className={styles.dSecretPanelTitle}>✅ 秘密健康状态</div>
                <div className={styles.dSecretHealthItems}>
                  <div>🟢 已公开秘密: 1 (无需追踪)</div>
                  <div>🟡 活跃秘密: 3</div>
                  <div>🔴 高债务 (&gt;30): 2</div>
                  <div>📈 建议揭露: 1 (天象核心)</div>
                </div>
                <div className={styles.dSecretSuggestion}>
                  💡 建议在第 16 章安排关于"天象核心"的秘密揭露
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>
      <section className={styles.dMemorySection} style={{ marginTop: "var(--space-4)" }}>
        <div className={`${styles.dSectionCard} ${collapsedSections.has("char-knowledge") ? styles.collapsed : ""}`} id="dCard-character-knowledge">
          <div className={styles.dSectionCardHeader} onClick={() => toggleSection("char-knowledge")}>
            <div className={styles.dSectionCardTitle}>
              <span className={styles.dCardIcon} style={{ background: "rgba(99,102,241,0.1)", color: "var(--color-brand-indigo)" }}>👤</span>
              角色知识状态
            </div>
            <div className={styles.dSectionCardToggle}>
              <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
                <path d="M3.5 5.25L7 8.75l3.5-3.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            </div>
          </div>
          <div className={styles.dSectionCardBody}>
            <div className={styles.dCharKnowledgeGrid}>
              {SECRET_CHARACTERS.map((ch, i) => (
                <div key={i} className={styles.dCharKnowledgeCard}>
                  <div className={styles.dCharKnowledgeTop}>
                    <div className={styles.dCharKnowledgeAvatar}>
                      {["🌲", "🌸", "🍃", "👴"][i]}
                    </div>
                    <div>
                      <div className={styles.dCharKnowledgeName}>{ch}</div>
                      <div className={styles.dCharKnowledgeCount}>{`知道 ${SECRET_ROWS.filter(s => s.known[ch] === true).length} / 总 ${SECRET_ROWS.length} 个秘密`}</div>
                    </div>
                  </div>
                  <div className={styles.dCharKnowledgeList}>
                    {SECRET_ROWS.map((s, j) => (
                      <div key={j} className={s.known[ch] === true ? styles.dCharKnowledgeKnown : styles.dCharKnowledgeUnknown}>
                        {s.known[ch] === true ? "✅" : "❌"} {s.secret}
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>
    </div>
  );

  // ── Render: Desktop Content ──
  const dContent = (
    <div className={styles.dAppLayout}>
      <header className={styles.dAppHeader}>
        <div className={styles.dHeaderLeft}>
          <button className={styles.dBtnBack} onClick={() => router.back()} title="返回">
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
              <path d="M10 3L5 8l5 5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </button>
          <span className={styles.dHeaderTitle}>四库管理</span>
          <span className={styles.dHeaderProject}>{PROJECT_NAME}</span>
          {isLoading && <span className={styles.loadingBadge}>同步中…</span>}
          {loadError && <span className={styles.loadingBadge} style={{color:"var(--color-danger)"}} title={loadError}>回退模式</span>}
        </div>
        <div className={styles.dHeaderRight}>{dSearchBox}</div>
      </header>
      <div className={styles.dAppBody}>
        <aside className={styles.dSidebar}>
          <div className={styles.dSidebarSectionLabel}>知识库</div>
          <nav className={styles.dVaultTabs}>
            {apiSidebarTabs.map((tab) => (
              <div
                key={tab.id}
                className={`${styles.dVaultTab} ${activeTab === tab.id ? styles.active : ""}`}
                data-tab={tab.id}
                onClick={() => setActiveTab(tab.id)}
              >
                <div className={`${styles.dTabIcon}`}>{tab.icon}</div>
                <div className={styles.dTabText}>
                  <span className={styles.dTabLabel}>{tab.label}</span>
                  <span className={styles.dTabCount}>{tab.count}</span>
                </div>
              </div>
            ))}
          </nav>
          <div className={styles.dSidebarDivider}></div>
          {dSidebarStats}
        </aside>
        <main className={styles.dContentArea}>
          {dCharacterPanel}
          {dTimelinePanel}
          {dCommitmentsPanel}
          {dWorldPanel}
          {dSecretsPanel}
        </main>
      </div>
      {renderCharModal()}
    </div>
  );

  // ── Render: Mobile Content ──
  const mTabColors = ["var(--tab-char)", "var(--tab-time)", "var(--tab-plot)", "var(--tab-world)"];
  const mTabLabels = ["人物库", "时间线库", "剧情承诺库", "世界观库"];

  const mContent = (
    <div className={styles.mShell}>
      {/* Status Bar */}
      <div className={styles.mStatusBar}>
        <span className={styles.mTime}>9:41</span>
        <span className={styles.mIcons}>
          <svg width="16" height="12" viewBox="0 0 16 12" fill="currentColor">
            <rect x="0" y="6" width="3" height="6" rx="0.5" />
            <rect x="4" y="4" width="3" height="8" rx="0.5" />
            <rect x="8" y="2" width="3" height="10" rx="0.5" />
            <rect x="12" y="0" width="3" height="12" rx="0.5" opacity="0.3" />
          </svg>
          <svg width="16" height="12" viewBox="0 0 16 12" fill="currentColor">
            <path d="M8 2C5.5 2 3.2 3 1.5 4.6L0 3.1C2.1 1.1 4.9 0 8 0s5.9 1.1 8 3.1L14.5 4.6C12.8 3 10.5 2 8 2z" opacity="0.3" />
            <path d="M8 5c1.6 0 3 .6 4.1 1.7L10.6 8.2C9.9 7.5 9 7 8 7s-1.9.5-2.6 1.2L3.9 6.7C5 5.6 6.4 5 8 5z" opacity="0.6" />
            <circle cx="8" cy="10.5" r="1.5" />
          </svg>
          <svg width="25" height="12" viewBox="0 0 25 12" fill="currentColor">
            <rect x="0" y="1" width="21" height="10" rx="2" fill="none" stroke="currentColor" strokeWidth="1" />
            <rect x="1.5" y="2.5" width="14" height="7" rx="1" fill="#34d399" />
            <rect x="22" y="4" width="2" height="4" rx="0.5" />
          </svg>
        </span>
      </div>

      {/* Top Nav */}
      <div className={styles.mTopNav}>
        <button className={styles.mBackBtn} onClick={() => router.back()}>←</button>
        <span className={styles.mTitle}>{PROJECT_NAME}</span>
        <button className={styles.mSearchBtn}>🔍</button>
      </div>

      {/* Tab Bar */}
      <div className={styles.mTabBarWrapper}>
        <div className={styles.mTabBar}>
          {mTabLabels.map((label, i) => (
            <div
              key={i}
              className={`${styles.mTabItem} ${mobileTab === i ? styles.active : ""}`}
              onClick={() => setMobileTab(i)}
            >
              {label}
              <span className={styles.mIndicator} style={{ background: mTabColors[i], width: mobileTab === i ? "24px" : "0" }}></span>
            </div>
          ))}
        </div>
      </div>

      {/* Tab 0: Characters */}
      <div className={`${styles.mTabContent} ${mobileTab === 0 ? styles.active : ""}`}>
        <div className={styles.mSearchBox}>
          <span className={styles.mSearchIcon}>🔍</span>
          <input
            type="text"
            placeholder="搜索角色..."
            value={mobileSearchQuery}
            onChange={(e) => setMobileSearchQuery(e.target.value)}
          />
        </div>
        {filteredMobileChars.map((char, i) => (
          <div key={i} className={`${styles.mCharCard} ${expandedCharCards.has(i) ? styles.expanded : ""}`} onClick={() => toggleMobileChar(i)}>
            <div className={styles.mCharHeader}>
              <div className={`${styles.mCharAvatar} ${styles[`mv${char.avatarVariant}`]}`}>{char.avatarChar}</div>
              <div className={styles.mCharInfo}>
                <div className={styles.mCharName}>{char.name}</div>
                <div className={styles.mCharTags}>
                  {char.tags.slice(0, 3).map((tag, j) => (
                    <span key={j} className={`${styles.mCharTag} ${j === 0 ? styles.mRoleTag : ""}`}>{tag}</span>
                  ))}
                </div>
              </div>
              <span className={styles.mCharArrow}>▼</span>
            </div>
            <div className={styles.mCharDetail}>
              <div className={styles.mCharDetailInner}>
                <div className={styles.mCharTraits}>
                  {char.traits.map((t, j) => <span key={j}>{t}</span>)}
                </div>
                <div className={styles.mCharDesc}>{char.desc}</div>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Tab 1: Timeline */}
      <div className={`${styles.mTabContent} ${mobileTab === 1 ? styles.active : ""}`}>
        <div className={styles.mTimeline}>
          {activeMobileTimeline.map((evt, i) => (
            <div key={i} className={`${styles.mTlNode} ${evt.className ? styles[evt.className] : ""}`}>
              <div className={styles.mTlDot}></div>
              <div className={styles.mTlLabel}>{evt.day}{evt.className === "current" ? <span className={styles.mTlBadge}>当前</span> : ""}</div>
              <div className={styles.mTlTitle}>{evt.title}</div>
              <div className={styles.mTlCard}>{evt.desc}</div>
            </div>
          ))}
        </div>
      </div>

      {/* Tab 2: Plot Promises */}
      <div className={`${styles.mTabContent} ${mobileTab === 2 ? styles.active : ""}`}>
        <div className={styles.mFilterBar}>
          {(["all", "pending", "done"] as const).map((type) => (
            <button
              key={type}
              className={`${styles.mFilterBtn} ${mobilePlotFilter === type ? styles.active : ""}`}
              onClick={() => setMobilePlotFilter(type)}
            >
              {type === "all" ? "全部" : type === "pending" ? "待回收" : "已回收"}
            </button>
          ))}
        </div>
        {filteredMobilePlot.map((item, i) => (
          <div key={i} className={`${styles.mPlotCard} ${item.type === "pending" ? styles.pending : styles.done} ${expandedPlotCards.has(i) ? styles.expanded : ""}`} onClick={() => toggleMobilePlot(i)}>
            <div className={styles.mPlotHeader}>
              <span className={styles.mPlotIcon}>{item.type === "pending" ? "🔴" : "🟢"}</span>
              <div className={styles.mPlotInfo}>
                <div className={styles.mPlotTitle}>{item.title}</div>
                <div className={styles.mPlotMeta}>{item.chapter}</div>
              </div>
              <span className={`${styles.mPlotStatus} ${item.type}`}>{item.type === "pending" ? "待回收" : "已回收"}</span>
              <span className={styles.mPlotExpand}>▼</span>
            </div>
            <div className={styles.mPlotDetail}>
              <div className={styles.mPlotDetailInner}>
                {item.desc}
                {item.suggest && <div className={styles.mPlotSuggest}>{item.suggest}</div>}
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Tab 3: World */}
      <div className={`${styles.mTabContent} ${mobileTab === 3 ? styles.active : ""}`}>
        <div className={styles.mCatBar}>
          {(["all", "geo", "his", "sys", "power"] as const).map((cat) => (
            <button
              key={cat}
              className={`${styles.mCatBtn} ${mobileWorldFilter === cat ? styles.active : ""}`}
              onClick={() => setMobileWorldFilter(cat)}
            >
              {cat === "all" ? "全部" : cat === "geo" ? "地理" : cat === "his" ? "历史" : cat === "sys" ? "体系" : "势力"}
            </button>
          ))}
        </div>
        <div className={styles.mWorldGrid}>
          {filteredMobileWorld.map((card, i) => (
            <div key={i} className={styles.mWorldCard}>
              <div className={`${styles.mWorldIcon} ${styles[card.iconClass]}`}>{card.icon}</div>
              <div className={styles.mWorldName}>{card.name}</div>
              <span className={`${styles.mWorldCat} ${styles[card.iconClass]}`}>{catLabel(card.cat)}</span>
              <div className={styles.mWorldDesc}>{card.desc}</div>
            </div>
          ))}
        </div>
      </div>

      {/* Bottom Nav */}
      <div className={styles.mBottomNav}>
        {[
          { icon: "🏠", label: "首页", onClick: () => router.push('/projects') },
          { icon: "📖", label: "作品", onClick: () => router.push('/projects'), active: true },
          { icon: "✏️", label: "创作", onClick: () => router.push(`/workspace/${projectId}`) },
          { icon: "👤", label: "我的", onClick: () => router.push('/settings') },
        ].map((item, i) => (
          <div key={i} className={`${styles.mNavItem} ${i === 1 ? styles.active : ""}`} onClick={item.onClick}>
            <span className={styles.mNavIcon}>{item.icon}</span>
            <span className={styles.mNavLabel}>{item.label}</span>
          </div>
        ))}
      </div>
    </div>
  );

  return (
    <>
      <div className={styles.desktopShell}>{dContent}</div>
      <div className={styles.mobileShell}>{mContent}</div>
    </>
  );
}

function catLabel(cat: string): string {
  const map: Record<string, string> = { geo: "地理", sys: "体系", his: "历史", power: "势力" };
  return map[cat] || cat;
}
