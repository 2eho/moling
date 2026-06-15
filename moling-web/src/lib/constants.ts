/* ============================================
   墨灵 (Moling) — Constants & UI Safe Text
   ============================================ */

// ---- Route Path Constants ----

export const ROUTES = {
  HOME: "/",
  AUTH: "/auth",
  PROJECTS: "/projects",
  NEW_PROJECT: "/projects/new",
  WORKSPACE: "/workspace",
  workspace: (id: string) => `/workspace/${id}`,
} as const;

// ---- API Endpoint Constants ----

export const API_ENDPOINTS = {
  AUTH: {
    LOGIN: "/auth/login",
    REGISTER: "/auth/register",
    REFRESH: "/auth/refresh",
    RESET_PASSWORD: "/auth/reset-password",
    SET_PASSWORD: "/auth/set-password",
    ME: "/auth/me",
  },
  PROJECTS: {
    LIST: "/projects",
    STATS: "/projects/stats",
    CREATE: "/projects",
    BY_ID: (id: string) => `/projects/${id}`,
  },
  CHAPTERS: {
    CURRENT: "/chapters/current",
    LIST: "/chapters",
    BY_ID: (id: string) => `/chapters/${id}`,
    CREATE: "/chapters",
  },
  CARDS: {
    POOL: "/cards/pool",
    DRAW: "/cards/draw",
    REDRAW: "/cards/redraw",
  },
  GENERATION: {
    GENERATE: "/projects/{projectId}/chapters/{chapterId}/generate",
    STATUS: "/generate/{taskId}/status",
    CANCEL: "/generate/{taskId}/cancel",
  },
  VAULT: {
    CHARACTERS: "/projects/{projectId}/vault/characters",
    TIMELINE: "/projects/{projectId}/vault/timeline",
    PLOT_PROMISES: "/projects/{projectId}/vault/plot-promises",
    WORLD: "/projects/{projectId}/vault/world",
  },
  HEALTH: {
    ALERTS: "/projects/{projectId}/health",
    REFRESH: "/projects/{projectId}/health/refresh",
  },
} as const;

// ---- UI Safe Text Replacements ----

/** 替代"Phase 4 运行中" */
export const PHASE4_RUNNING = "正在同步世界设定…";

/** 替代"Phase 4 已完成" */
export const PHASE4_DONE = "设定已同步";

/** 替代"Dynamic Layer Summary" */
export const DYNAMIC_LAYER_SUMMARY = "📋 当前上下文已就绪";

/** 替代"Conflict Warning" */
export const CONFLICT_WARNING = "⚠️ 组合偏好提示";

/** 替代"Cooldown Text" — 保留 {used}/{max} 占位符 */
export const COOLDOWN_TEXT = "🔄 今日可重抽 {used}/{max} 次";

/** 生成阶段文案（替代技术术语） */
export const GENERATION_STAGES = ["预处理中…", "生成中…", "校验中…"];

/** 新推荐卡牌标签 */
export const FRESH_CARD_LABEL = "🔥 新推荐（近期生成·优先出现）";

/** 卡牌来源 — Phase 4 来源 {n} 为章节号 */
export const CARD_SOURCE_PHASE4 = "📌 第{n}章 · 收纳生成";

/** 刷新设定按钮文案 */
export const REFRESH_SETTING = "刷新故事设定";

/** 待同步提示 */
export const VAULT_PENDING = "有 N 章内容待同步";

// ---- Template Data ----
export interface Template {
  id: string;
  name: string;
  description: string;
  genre: string;
  worldSuggestion: string;
  protagonistSuggestion: string;
  icon: string;
}

export const TEMPLATES: Template[] = [
  {
    id: "template-xhxx",
    name: "玄幻修仙",
    description: "修炼长生、逆天改命的东方玄幻世界",
    genre: "玄幻修仙",
    worldSuggestion:
      "一个以修仙为主流的架空世界，分为凡人界与修真界。灵脉分布于名山大川，妖兽横行于荒郊野外。各大宗门割据一方，正邪势力明争暗斗。",
    protagonistSuggestion: "一位出身平凡但天赋异禀的少年，因机缘巧合获得远古传承",
    icon: "☯",
  },
  {
    id: "template-dsya",
    name: "都市言情",
    description: "现代都市背景下的情感故事与生活",
    genre: "都市言情",
    worldSuggestion:
      "现代都市背景，可以是繁华的一线城市或是宁静的小城镇。主角们在都市中追逐梦想、经营爱情、面对现实的种种挑战。",
    protagonistSuggestion: "一位怀揣梦想的都市青年，在职场与情感中成长",
    icon: "🏙",
  },
  {
    id: "template-kfmao",
    name: "科幻冒险",
    description: "星际探索、未来科技与未知文明的壮丽史诗",
    genre: "科幻冒险",
    worldSuggestion:
      "近未来或远未来的科幻世界观。星际航行技术已经成熟，人类足迹遍布多个星系。存在着各种外星文明与未知的宇宙现象。",
    protagonistSuggestion: "一位勇敢的探索者或科学家，面对未知挑战永不言弃",
    icon: "🚀",
  },
];

// ---- Genre Options ----

export const GENRE_OPTIONS = [
  "玄幻修仙",
  "都市言情",
  "科幻冒险",
  "古代言情",
  "悬疑推理",
  "游戏竞技",
  "轻小说",
  "历史军事",
] as const;

// ---- Rarity Enum & Labels ----

export const RARITY_LABELS: Record<string, string> = {
  common: "普通",
  rare: "稀有",
  epic: "史诗",
  legendary: "传说",
};

export const RARITY_ICONS: Record<string, string> = {
  common: "⚪",
  rare: "🔵",
  epic: "🟣",
  legendary: "🟠",
};

export const RARITY_ORDER: Record<string, number> = {
  common: 0,
  rare: 1,
  epic: 2,
  legendary: 3,
};

// ---- Project Status Labels ----

export const PROJECT_STATUS_LABELS: Record<string, string> = {
  draft: "草稿",
  active: "活跃中",
  completed: "已完成",
  archived: "已归档",
};

// ---- Chapter Status Labels ----

export const CHAPTER_STATUS_LABELS: Record<string, string> = {
  draft: "草稿",
  generating: "生成中",
  completed: "已完成",
  revised: "已修订",
};

// ---- Draw Mode Labels ----

export const DRAW_MODE_LABELS: Record<string, string> = {
  normal: "单线",
  double: "双线",
  guaranteed: "全线",
};

export const DRAW_MODE_OPTIONS = [
  { value: "normal", label: "单线" },
  { value: "double", label: "双线" },
  { value: "guaranteed", label: "全线" },
  { value: "mixed", label: "混合" },
] as const;

// ---- Vault Tab Labels ----

export const VAULT_TABS = [
  { id: "characters", label: "角色库", icon: "👤" },
  { id: "timeline", label: "时间线", icon: "📅" },
  { id: "plot-promises", label: "剧情承诺", icon: "🎯" },
  { id: "world", label: "世界观", icon: "🌍" },
] as const;

// ---- Health Alert Severity Labels ----

export const HEALTH_SEVERITY_LABELS: Record<string, string> = {
  info: "提示",
  warning: "警告",
  critical: "严重",
};

// ---- Misc ----

export const MAX_REDRAW_COUNT = 3;

export const AUTH_PAGE_TABS = [
  { id: "login", label: "登录" },
  { id: "register", label: "注册" },
  { id: "reset", label: "重置密码" },
] as const;

export const CREATION_MODES = [
  {
    id: "from_scratch",
    title: "从零开始",
    description: "自由设定小说的世界观、角色和大纲，完全掌控创作方向",
    icon: "✍",
  },
  {
    id: "from_template",
    title: "使用模板",
    description: "从预设模板出发快速搭建故事框架，适合新手快速上手",
    icon: "📋",
  },
] as const;
