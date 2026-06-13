/* ============================================
   墨灵 (Moling) — Mock Handler Registration
   ============================================
   注册所有 mock 数据到 apiClient，
   当 NEXT_PUBLIC_MOCK_ENABLED=true 时自动生效。
   ============================================ */

import { registerMock } from "@/lib/apiClient";
import { mockProjects } from "./projects";
import { mockChapters } from "./chapters";
import { mockCards } from "./cards";
import { mockCharacters, mockTimelines, mockPlotPromises, mockWorlds } from "./vault";
import { mockHealthAlerts } from "./health";
import type { ApiResponse, Project, Chapter, VaultCharacterRelationship } from "@/lib/types";

// ---- Helpers ----

let requestCounter = 0;
function nextRequestId(): string {
  requestCounter += 1;
  return `mock-req-${String(requestCounter).padStart(4, "0")}`;
}

function ok<T>(data: T, message = "success"): ApiResponse<T> {
  return { code: 200, message, data, request_id: nextRequestId() };
}

function created<T>(data: T, message = "created"): ApiResponse<T> {
  return { code: 201, message, data, request_id: nextRequestId() };
}

function paginate<T>(items: T[], page = 1, pageSize = 20) {
  const start = (page - 1) * pageSize;
  const paged = items.slice(start, start + pageSize);
  return ok({ items: paged, total: items.length, page, page_size: pageSize });
}

function findItem<T extends { id: string }>(items: T[], id: string, label: string): T {
  const item = items.find((i) => i.id === id);
  if (!item) throw new Error(`${label} ${id} not found`);
  return item;
}

// =========================================
//  Auth
// =========================================

registerMock("POST:/auth/login", (body: unknown) => {
  const { email, password } = body as Record<string, string>;
  if (email === "test@moling.com" && password === "123456") {
    return ok({
      user: { id: "user-001", email, username: "墨灵用户", status: "active" },
      access_token: "mock-access-token-user-001",
      refresh_token: "mock-refresh-token-user-001",
    });
  }
  return {
    code: 401,
    message: "邮箱或密码错误",
    data: null,
    request_id: nextRequestId(),
  };
});

registerMock("POST:/auth/register", (body: unknown) => {
  const { email, nickname } = body as Record<string, string>;
  // G1 修复：注册响应不返回 token（符合文档）
  return created({
    user: { id: "user-002", email, nickname, status: "active" },
  });
});

registerMock("POST:/auth/refresh", () => {
  return ok({
    access_token: "mock-access-token-refreshed",
    refresh_token: "mock-refresh-token-refreshed",
  });
});

registerMock("GET:/auth/me", () => {
  return ok({
    id: "user-001",
    email: "test@moling.com",
    username: "墨灵用户",
    avatar_url: null,
    status: "active",
    created_at: "2025-01-01T00:00:00Z",
    updated_at: "2025-06-12T00:00:00Z",
  });
});

registerMock("POST:/auth/reset-password", () => {
  return ok(null, "密码重置邮件已发送");
});

// =========================================
//  Projects
// =========================================

let nextProjectId = 100;
const projectsState = [...mockProjects];

registerMock("GET:/projects", (_, params) => {
  const p = params as Record<string, string | number | boolean | undefined> || {};
  const page = Number(p.page) || 1;
  const pageSize = Number(p.page_size) || 20;
  const search = p.search as string | undefined;
  const status = p.status as string | undefined;
  const genre = p.genre as string | undefined;

  let filtered = [...projectsState];
  if (search) {
    const q = search.toLowerCase();
    filtered = filtered.filter(
      (pr) =>
        pr.title.toLowerCase().includes(q) ||
        pr.synopsis?.toLowerCase().includes(q),
    );
  }
  if (status) filtered = filtered.filter((pr) => pr.status === status);
  if (genre) filtered = filtered.filter((pr) => pr.genre === genre);

  return paginate(filtered, page, pageSize);
});

registerMock("GET:/projects/stats", () => {
  const total = projectsState.length;
  const active = projectsState.filter((p) => p.status === "active").length;
  const draft = projectsState.filter((p) => p.status === "draft").length;
  const total_words = projectsState.reduce((s, p) => s + p.word_count, 0);
  const today_words = 0; // G2 修复：补充 today_words 字段
  return ok({ total_projects: total, active, draft, total_words, today_words });
});

registerMock("POST:/projects", (body: unknown) => {
  const data = body as Partial<Project>;
  nextProjectId += 1;
  const now = new Date().toISOString();
  const newProject: Project = {
    id: `proj-${String(nextProjectId).padStart(3, "0")}`,
    title: data.title || "未命名项目",
    author: "墨灵用户",
    genre: data.genre || "未分类",
    tags: data.tags || [],
    synopsis: data.synopsis || "",
    worldview: data.worldview || "",
    protagonist: data.protagonist || "",
    supporting_chars: data.supporting_chars || "",
    word_count: 0,
    target_words: data.target_words || 200000,
    frequency: data.frequency || "",
    status: "draft",
    creation_mode: (data.creation_mode as Project["creation_mode"]) || "from_scratch",
    created_at: now,
    updated_at: now,
  };
  projectsState.unshift(newProject);
  return created(newProject);
});

registerMock("GET:/projects/{id}", (_, params) => {
  const { id } = params as Record<string, string>;
  return ok(findItem(projectsState, id, "Project"));
});

registerMock("PUT:/projects/{id}", (body, params) => {
  const { id } = params as Record<string, string>;
  const project = findItem(projectsState, id, "Project");
  const updates = body as Partial<Project>;
  Object.assign(project, { ...updates, updated_at: new Date().toISOString() });
  return ok(project);
});

registerMock("DELETE:/projects/{id}", (_, params) => {
  const { id } = params as Record<string, string>;
  const idx = projectsState.findIndex((p) => p.id === id);
  if (idx === -1) throw new Error("Project not found");
  projectsState.splice(idx, 1);
  // G3 修复：返回 {deleted, id} 格式（前端期望）
  return ok({ deleted: true, id });
});

// =========================================
//  Chapters
// =========================================

let nextChapterNum = 4;
const chaptersState = [...mockChapters];

registerMock("GET:/projects/{projectId}/chapters/current", (_, params) => {
  const { projectId } = params as Record<string, string>;
  const found = chaptersState
    .filter((c) => c.project_id === projectId)
    .sort((a, b) => b.chapter_number - a.chapter_number);
  return ok(found[0] || null);
});

registerMock("GET:/projects/{projectId}/chapters", (_, params) => {
  const { projectId } = params as Record<string, string>;
  const list = chaptersState
    .filter((c) => c.project_id === projectId)
    .sort((a, b) => a.chapter_number - b.chapter_number);
  return ok(list);
});

registerMock("POST:/projects/{projectId}/chapters", (body, params) => {
  const { projectId } = params as Record<string, string>;
  if (!projectId) throw new Error("project_id is required");
  const data = body as Partial<Chapter>;
  const now = new Date().toISOString();
  const newChapter: Chapter = {
    id: `ch-${String(nextChapterNum).padStart(3, "0")}`,
    project_id: projectId,
    title: data.title || `第${nextChapterNum}章`,
    content: data.content || "",
    chapter_number: nextChapterNum,
    status: "draft",
    word_count: 0,
    created_at: now,
    updated_at: now,
  };
  nextChapterNum += 1;
  chaptersState.push(newChapter);
  return created(newChapter);
});

registerMock("GET:/projects/{projectId}/chapters/{id}", (_, params) => {
  const { id } = params as Record<string, string>;
  return ok(findItem(chaptersState, id, "Chapter"));
});

registerMock("PATCH:/projects/{projectId}/chapters/{id}", (body, params) => {
  const { id } = params as Record<string, string>;
  const chapter = findItem(chaptersState, id, "Chapter");
  const updates = body as Partial<Chapter>;
  Object.assign(chapter, {
    ...updates,
    word_count: updates.content
      ? updates.content.replace(/\s/g, "").length
      : chapter.word_count,
    updated_at: new Date().toISOString(),
  });
  return ok(chapter);
});

registerMock("DELETE:/projects/{projectId}/chapters/{id}", (_, params) => {
  const { id } = params as Record<string, string>;
  const idx = chaptersState.findIndex((c) => c.id === id);
  if (idx === -1) throw new Error("Chapter not found");
  chaptersState.splice(idx, 1);
  return ok(null, "章节已删除");
});

// =========================================
//  Cards
// =========================================

const cardsState = [...mockCards];

registerMock("GET:/cards/pool", (_, params) => {
  const p = params as Record<string, string> || {};
  const projectId = p.project_id;
  return ok(cardsState.filter((c) => c.project_id === projectId));
});

registerMock("POST:/cards/draw", (body) => {
  const { keep_card_ids, weights, mode } = body as Record<string, unknown>;
  return created({
    id: `draw-${Date.now()}`,
    project_id: "proj-001",
    chapter_id: "ch-003",
    card_ids: keep_card_ids,
    weights,
    mode,
    draw_round: 1,
    remaining_redraws: 2,
  });
});

// =========================================
//  Generation
// =========================================

let taskIdCounter = 0;
// 模拟任务进度递增（每次轮询前进 15%）
const taskProgressMap = new Map<string, number>();

registerMock("POST:/generation/trigger", () => {
  taskIdCounter += 1;
  const taskId = `task-gen-${taskIdCounter}`;
  taskProgressMap.set(taskId, 0);
  return created({
    id: taskId,
    project_id: "proj-001",
    chapter_id: "ch-003",
    task_type: "generate_chapter",
    status: "running",
    progress_stage: "分析中",
    progress_percent: 0,
  });
});

registerMock("GET:/generation/task/{taskId}", (_, params) => {
  const { taskId } = params as Record<string, string>;
  const current = taskProgressMap.get(taskId) ?? 0;
  const next = Math.min(current + 15, 100);
  taskProgressMap.set(taskId, next);

  const stages = ["分析中", "编织中", "润色中", "完成"];
  const stageIndex = Math.min(Math.floor(next / 30), stages.length - 1);

  return ok({
    id: taskId,
    project_id: "proj-001",
    chapter_id: "ch-003",
    task_type: "generate_chapter",
    status: next >= 100 ? "completed" : "running",
    progress_stage: stages[stageIndex],
    progress_percent: next,
  });
});

registerMock("POST:/generation/task/{taskId}/cancel", () => {
  return ok(null, "任务已取消");
});

registerMock("POST:/projects/{projectId}/chapters/{chapterId}/confirm", () => {
  return ok(null, "章节已确认");
});

registerMock("POST:/projects/{projectId}/chapters/{chapterId}/revise", () => {
  return ok(null, "章节已提交修改");
});

// =========================================
//  Vault
// =========================================

const charactersState = [...mockCharacters];
const timelinesState = [...mockTimelines];
const plotPromisesState = [...mockPlotPromises];
const worldsState = [...mockWorlds];

registerMock("GET:/projects/{projectId}/vault/characters", (_, params) => {
  const { projectId } = params as Record<string, string>;
  return ok(charactersState.filter((c) => c.project_id === projectId));
});

registerMock("GET:/projects/{projectId}/vault/timeline", (_, params) => {
  const { projectId } = params as Record<string, string>;
  return ok(timelinesState.filter((t) => t.project_id === projectId));
});

registerMock("GET:/projects/{projectId}/vault/plot-promises", (_, params) => {
  const { projectId } = params as Record<string, string>;
  return ok(plotPromisesState.filter((p) => p.project_id === projectId));
});

registerMock("GET:/projects/{projectId}/vault/world", (_, params) => {
  const { projectId } = params as Record<string, string>;
  return ok(worldsState.filter((w) => w.project_id === projectId));
});

// =========================================
//  Health
// =========================================

const healthState = [...mockHealthAlerts];

registerMock("GET:/projects/{projectId}/health/alerts", () => {
  return ok(healthState.filter((a) => a.is_active));
});

registerMock("POST:/projects/{projectId}/health/refresh", () => {
  // Simulate a fresh check — flip alert statuses occasionally
  return ok(healthState.filter((a) => a.is_active));
});

// =========================================
//  Settings (D1, G4)
// =========================================

const settingsState: Record<string, unknown> = {
  id: "settings-001",
  user_id: "user-001",
  theme: "system",
  language: "zh-CN",
  editor_font_size: 14,
  editor_line_height: 1.6,
  auto_save_interval: 30,
  generation_preference: {
    default_mode: "balanced",
    default_weights: { plot: 0.3, character: 0.3, worldview: 0.2, style: 0.2 },
    auto_confirm: false,
  },
  notification_settings: {
    email_enabled: true,
    push_enabled: true,
    types: {
      generation_complete: true,
      health_alert: true,
      system: true,
      subscription: false,
      chapter_ready: true,
    },
  },
  created_at: "2025-01-01T00:00:00Z",
  updated_at: "2025-06-12T00:00:00Z",
};

registerMock("GET:/settings", () => {
  return ok(settingsState);
});

registerMock("PATCH:/settings", (body: unknown) => {
  const updates = body as Record<string, unknown>;
  Object.assign(settingsState, updates, { updated_at: new Date().toISOString() });
  return ok(settingsState);
});

registerMock("GET:/settings/health-monitor", () => {
  return ok({
    enabled: true,
    check_interval: 300,
    rules: ["r1_continuity", "r2_character_consistency", "r3_plot_promise"],
  });
});

registerMock("GET:/settings/phase4-review", () => {
  return ok({
    auto_approve: false,
    pending_count: 0,
    last_review_at: null,
  });
});

registerMock("POST:/settings/export", () => {
  return ok({ export_url: "https://mock.moling.com/export/settings-001.zip" });
});

registerMock("POST:/settings/clear-cache", () => {
  return ok({ cleared: true });
});

// =========================================
//  Notifications (D2, G4)
// =========================================

const notificationsState = [
  {
    id: "notif-001",
    user_id: "user-001",
    type: "generation_complete",
    title: "章节生成完成",
    message: "第3章已生成完毕，点击查看",
    is_read: false,
    related_id: "ch-003",
    related_type: "chapter",
    created_at: "2025-06-12T10:00:00Z",
  },
  {
    id: "notif-002",
    user_id: "user-001",
    type: "health_alert",
    title: "健康检查警告",
    message: "角色「李明」在最近3章中行为不一致",
    is_read: true,
    related_id: "alert-001",
    related_type: "health_alert",
    created_at: "2025-06-11T08:00:00Z",
  },
];

registerMock("GET:/notifications", (_, params) => {
  const p = params as Record<string, string | boolean | undefined> || {};
  let filtered = [...notificationsState];
  if (p.unread_only) {
    filtered = filtered.filter((n) => !n.is_read);
  }
  return ok(filtered);
});

registerMock("PATCH:/notifications/{notificationId}/read", (_, params) => {
  const { notificationId } = params as Record<string, string>;
  const notif = notificationsState.find((n) => n.id === notificationId);
  if (!notif) throw new Error("Notification not found");
  notif.is_read = true;
  return ok(notif);
});

registerMock("PATCH:/notifications/read-all", () => {
  notificationsState.forEach((n) => { n.is_read = true; });
  return ok({ updated: notificationsState.length });
});

// =========================================
//  Subscription (D3, G4)
// =========================================

const subscriptionPlans = [
  {
    id: "free",
    name: "免费版",
    price: 0,
    features: ["1个项目", "每月1万字", "基础卡牌"],
    limits: { projects: 1, words_per_month: 10000, cards_per_project: 20 },
  },
  {
    id: "pro",
    name: "专业版",
    price: 29,
    features: ["无限项目", "每月50万字", "高级卡牌", "Phase 4自动收纳"],
    limits: { projects: -1, words_per_month: 500000, cards_per_project: 100 },
  },
  {
    id: "team",
    name: "团队版",
    price: 99,
    features: ["所有专业版功能", "团队协作", "API访问"],
    limits: { projects: -1, words_per_month: -1, cards_per_project: -1 },
  },
];

const currentSubscription = {
  id: "sub-001",
  user_id: "user-001",
  plan: "free",
  status: "active",
  current_period_start: "2025-06-01T00:00:00Z",
  current_period_end: "2026-06-01T00:00:00Z",
  cancel_at_period_end: false,
  created_at: "2025-06-01T00:00:00Z",
};

registerMock("GET:/subscription/plans", () => {
  return ok(subscriptionPlans);
});

registerMock("POST:/subscription/create-checkout", (body: unknown) => {
  const { plan } = body as Record<string, string>;
  return ok({
    checkout_url: `https://mock-checkout.moling.com/${plan}`,
    session_id: `sess-${Date.now()}`,
  });
});

registerMock("GET:/subscription/current", () => {
  return ok(currentSubscription);
});

registerMock("POST:/subscription/cancel", () => {
  currentSubscription.cancel_at_period_end = true;
  return ok(currentSubscription);
});

// =========================================
//  Secrets (D4, G4)
// =========================================

const secretsState = [
  {
    id: "secret-001",
    project_id: "proj-001",
    character_id: "char-001",
    character_name: "李明",
    secrets: [
      { id: "s-001", content: "李明的真实身份是卧底", related_characters: ["char-002"], confidence: 0.9, source_chapter: 5 },
    ],
    relationships: [
      { from_character_id: "char-001", to_character_id: "char-002", secret_count: 1, tension_level: 0.8 },
    ],
  },
];

registerMock("GET:/projects/{projectId}/secrets", (_, params) => {
  const { projectId } = params as Record<string, string>;
  return ok(secretsState.filter((s) => s.project_id === projectId));
});

registerMock("GET:/projects/{projectId}/secrets/character/{characterId}", (_, params) => {
  const { projectId, characterId } = params as Record<string, string>;
  const secret = secretsState.find((s) => s.project_id === projectId && s.character_id === characterId);
  if (!secret) throw new Error("Secret not found");
  return ok(secret);
});

registerMock("PATCH:/projects/{projectId}/secrets/character/{characterId}", (body, params) => {
  const { projectId, characterId } = params as Record<string, string>;
  const secret = secretsState.find((s) => s.project_id === projectId && s.character_id === characterId);
  if (!secret) throw new Error("Secret not found");
  Object.assign(secret, body as Record<string, unknown>);
  return ok(secret);
});

// =========================================
//  Templates (D7, G4)
// =========================================

const templatesState = [
  {
    id: "tpl-001",
    name: "经典三幕式",
    description: "遵循三幕结构的经典小说模板",
    genre: "fantasy",
    structure: [
      { title: "第一幕：设定与冲突", outline: "引入主角和世界设定", word_count_target: 30000, chapter_type: "setup" },
      { title: "第二幕：冒险与成长", outline: "主角面临挑战和成长", word_count_target: 120000, chapter_type: "development" },
      { title: "第三幕：高潮与结局", outline: "解决主要冲突", word_count_target: 50000, chapter_type: "climax" },
    ],
    created_at: "2025-01-01T00:00:00Z",
    is_official: true,
  },
];

registerMock("GET:/templates", (_, params) => {
  const p = params as Record<string, string | undefined> || {};
  let filtered = [...templatesState];
  if (p.genre) {
    filtered = filtered.filter((t) => t.genre === p.genre);
  }
  if (p.official_only === "true") {
    filtered = filtered.filter((t) => t.is_official);
  }
  return ok(filtered);
});

registerMock("GET:/templates/{templateId}", (_, params) => {
  const { templateId } = params as Record<string, string>;
  const tpl = templatesState.find((t) => t.id === templateId);
  if (!tpl) throw new Error("Template not found");
  return ok(tpl);
});

registerMock("POST:/templates", (body: unknown) => {
  const data = body as Record<string, unknown>;
  const newTpl = { ...data, id: `tpl-${Date.now()}`, is_official: false, created_at: new Date().toISOString() } as any;
  templatesState.push(newTpl);
  return created(newTpl);
});

registerMock("DELETE:/templates/{templateId}", (_, params) => {
  const { templateId } = params as Record<string, string>;
  const idx = templatesState.findIndex((t) => t.id === templateId);
  if (idx === -1) throw new Error("Template not found");
  templatesState.splice(idx, 1);
  return ok(null, "模板已删除");
});

// =========================================
//  Weave (D8, G4)
// =========================================

const weavePatternsState = [
  {
    id: "weave-001",
    name: "因果链",
    description: "事件之间通过因果关系紧密相连",
    type: "causal_chain",
    structure: {
      threads: [
        { id: "thread-001", name: "主线", thread_type: "main", importance: 1.0 },
      ],
      convergence_points: [10, 20, 30],
    },
    applicable_genres: ["mystery", "fantasy"],
  },
  {
    id: "weave-002",
    name: "平行叙事",
    description: "多条故事线平行发展，最终汇聚",
    type: "parallel",
    structure: {
      threads: [
        { id: "thread-001", name: "线索A", thread_type: "parallel", importance: 0.8 },
        { id: "thread-002", name: "线索B", thread_type: "parallel", importance: 0.8 },
      ],
      convergence_points: [25],
    },
    applicable_genres: ["thriller", "scifi"],
  },
];

registerMock("GET:/weave/patterns", () => {
  return ok(weavePatternsState);
});

registerMock("GET:/weave/patterns/{patternId}", (_, params) => {
  const { patternId } = params as Record<string, string>;
  const pattern = weavePatternsState.find((p) => p.id === patternId);
  if (!pattern) throw new Error("Pattern not found");
  return ok(pattern);
});

registerMock("POST:/projects/{projectId}/weave/apply", (body, params) => {
  const { projectId } = params as Record<string, string>;
  const { pattern_id } = body as Record<string, string>;
  return ok({ applied: true, pattern_id, project_id: projectId });
});

// =========================================
//  Import (D9, G4)
// =========================================

const importJobsState: Record<string, { job_id: string; status: string; progress: number }> = {};

registerMock("POST:/projects/{projectId}/import/jobs", (body, params) => {
  const { projectId } = params as Record<string, string>;
  const { source_type } = body as Record<string, string>;
  const jobId = `job-${Date.now()}`;
  importJobsState[jobId] = { job_id: jobId, status: "pending", progress: 0 };
  return created({ job_id: jobId, status: "pending", project_id: projectId, source_type });
});

registerMock("GET:/projects/{projectId}/import/jobs/{jobId}", (_, params) => {
  const { jobId } = params as Record<string, string>;
  const job = importJobsState[jobId];
  if (!job) throw new Error("Job not found");
  return ok(job);
});

registerMock("GET:/projects/{projectId}/import/jobs", () => {
  return ok({ jobs: Object.values(importJobsState) });
});

// =========================================
//  Save Draft (D10, G4)
// =========================================

let draftState: Record<string, { content: string; updated_at: string }> = {};

registerMock("POST:/projects/{projectId}/chapters/{chapterId}/draft", (body, params) => {
  const { projectId, chapterId } = params as Record<string, string>;
  const { content } = body as Record<string, string>;
  const key = `${projectId}-${chapterId}`;
  draftState[key] = { content, updated_at: new Date().toISOString() };
  return ok({ saved: true, draft_id: `draft-${Date.now()}`, project_id: projectId, chapter_id: chapterId });
});

registerMock("GET:/projects/{projectId}/chapters/{chapterId}/draft", (_, params) => {
  const { projectId, chapterId } = params as Record<string, string>;
  const key = `${projectId}-${chapterId}`;
  const draft = draftState[key];
  if (!draft) return ok(null);
  return ok(draft);
});

// =========================================
//  Chapter Suggestions/Agent (D11, G4)
// =========================================

registerMock("GET:/projects/{projectId}/chapters/{chapterId}/suggestions", () => {
  return ok({
    suggestions: [
      "可以考虑增加角色之间的冲突",
      "时间线的衔接可以更自然",
      "建议补充世界观细节",
    ],
  });
});

registerMock("POST:/projects/{projectId}/chapters/{chapterId}/agent", (body) => {
  const { instruction } = body as Record<string, string>;
  return ok({ task_id: `agent-${Date.now()}`, instruction, status: "running" });
});

// =========================================
//  Phase 4 Pending Reviews (D12, G4)
// =========================================

registerMock("GET:/phase4/pending-reviews", () => {
  return ok({
    reviews: [],
  });
});

registerMock("POST:/phase4/reviews/{reviewId}/approve", () => {
  return ok({ approved: true });
});

registerMock("POST:/phase4/reviews/{reviewId}/reject", () => {
  return ok({ rejected: true });
});

// =========================================
//  Draw History (D13, G4)
// =========================================

const drawHistoryState = [
  {
    id: "draw-001",
    project_id: "proj-001",
    chapter_id: "ch-003",
    draw_round: 1,
    cards_drawn: [
      { card_id: "card-001", card_name: "命运转折点", rarity: "epic", direction_type: "plot" },
      { card_id: "card-002", card_name: "角色成长", rarity: "rare", direction_type: "character" },
    ],
    mode: "normal",
    created_at: "2025-06-12T10:00:00Z",
  },
];

registerMock("GET:/projects/{projectId}/draw-history", (_, params) => {
  const { projectId } = params as Record<string, string>;
  const p = params as Record<string, string | number | undefined> || {};
  const page = Number(p.page) || 1;
  const pageSize = Number(p.page_size) || 20;
  const filtered = drawHistoryState.filter((d) => d.project_id === projectId);
  return paginate(filtered, page, pageSize);
});

registerMock("GET:/projects/{projectId}/draw-history/{drawId}", (_, params) => {
  const { drawId } = params as Record<string, string>;
  const draw = drawHistoryState.find((d) => d.id === drawId);
  if (!draw) throw new Error("Draw history not found");
  return ok(draw);
});

// =========================================
//  Admin (D14, G4)
// =========================================

registerMock("GET:/admin/stats", () => {
  return ok({
    total_users: 150,
    active_users: 45,
    total_projects: 280,
    total_words: 15000000,
    api_calls_today: 3200,
    error_rate: 0.02,
  });
});

const adminUsersState = [
  {
    id: "user-001",
    email: "test@moling.com",
    username: "墨灵用户",
    avatar_url: null,
    status: "active",
    created_at: "2025-01-01T00:00:00Z",
    updated_at: "2025-06-12T00:00:00Z",
    project_count: 3,
    total_words: 150000,
    last_active_at: "2025-06-12T10:00:00Z",
  },
];

registerMock("GET:/admin/users", (_, params) => {
  const p = params as Record<string, string | number | undefined> || {};
  const page = Number(p.page) || 1;
  const pageSize = Number(p.page_size) || 20;
  return paginate(adminUsersState, page, pageSize);
});

const adminProjectsState = [
  {
    id: "proj-001",
    title: "星渊行者",
    author: "墨灵用户",
    genre: "科幻",
    tags: ["太空歌剧", "探险"],
    word_count: 156780,
    target_words: 200000,
    status: "active",
    creation_mode: "from_scratch",
    created_at: "2025-03-15T08:00:00Z",
    updated_at: "2025-06-12T10:30:00Z",
    user_email: "test@moling.com",
    chapter_count: 12,
    health_score: 0.85,
  },
];

registerMock("GET:/admin/projects", (_, params) => {
  const p = params as Record<string, string | number | undefined> || {};
  const page = Number(p.page) || 1;
  const pageSize = Number(p.page_size) || 20;
  return paginate(adminProjectsState, page, pageSize);
});

registerMock("PATCH:/admin/users/{userId}", (body, params) => {
  const { userId } = params as Record<string, string>;
  const user = adminUsersState.find((u) => u.id === userId);
  if (!user) throw new Error("User not found");
  Object.assign(user, body as Record<string, unknown>, { updated_at: new Date().toISOString() });
  return ok(user);
});

// =========================================
//  Vault Character CRUD (D5, G4)
// =========================================

let nextCharId = 10;

registerMock("POST:/projects/{projectId}/vault/characters", (body, params) => {
  const { projectId } = params as Record<string, string>;
  const data = body as Record<string, unknown>;
  nextCharId += 1;
  const newChar = {
    id: `char-${String(nextCharId).padStart(3, "0")}`,
    project_id: projectId,
    name: data.name || "新角色",
    role: data.role || "supporting",
    description: data.description || "",
    traits: (data.traits as string[]) || [],
    background: data.background || "",
    arc: data.arc || "",
    relationships: (data.relationships as VaultCharacterRelationship[]) || [],
    location: data.location || "",
    appearance: data.appearance || "",
    personality: data.personality || "",
    knowledge: data.knowledge || "",
    confidence: data.confidence || 0.5,
  } as any;
  charactersState.push(newChar);
  return created(newChar);
});

registerMock("PATCH:/projects/{projectId}/vault/characters/{characterId}", (body, params) => {
  const { characterId } = params as Record<string, string>;
  const char = charactersState.find((c) => c.id === characterId);
  if (!char) throw new Error("Character not found");
  Object.assign(char, body as Record<string, unknown>);
  return ok(char);
});

registerMock("DELETE:/projects/{projectId}/vault/characters/{characterId}", (_, params) => {
  const { characterId } = params as Record<string, string>;
  const idx = charactersState.findIndex((c) => c.id === characterId);
  if (idx === -1) throw new Error("Character not found");
  charactersState.splice(idx, 1);
  return ok(null, "角色已删除");
});

// =========================================
//  Vault Summary (D6, G4)
// =========================================

registerMock("GET:/projects/{projectId}/vault/summary", (_, params) => {
  const { projectId } = params as Record<string, string>;
  return ok({
    project_id: projectId,
    characters_count: charactersState.filter((c) => c.project_id === projectId).length,
    timelines_count: timelinesState.filter((t) => t.project_id === projectId).length,
    plot_promises_count: plotPromisesState.filter((p) => p.project_id === projectId).length,
    worlds_count: worldsState.filter((w) => w.project_id === projectId).length,
    recent_characters: charactersState.filter((c) => c.project_id === projectId).slice(0, 5),
    active_plot_promises: plotPromisesState.filter((p) => p.project_id === projectId && p.status === "pending").slice(0, 5),
    recent_events: timelinesState.flatMap((t) => t.events).slice(0, 10),
  });
});
