/* ============================================
   墨灵 (Moling) — Real API Functions
   ============================================
   通过 apiClient 调用真实后端接口。
   ============================================ */

import { apiClient } from "@/lib/apiClient";
import type {
  ApiResponse,
  Project,
  Chapter,
  CardPool,
  DrawRecord,
  GenerationTask,
  VaultCharacter,
  VaultTimeline,
  VaultPlotPromise,
  VaultWorld,
  VaultSummary,
  HealthAlert,
  SystemHealthStatus,
  User,
  Notification,
  UserSettings,
  Subscription,
  SubscriptionPlanDetails,
  SecretMatrix,
  WeavePattern,
  Template,
  DrawHistory,
  AdminStats,
  AdminUser,
  AdminProject,
  Phase4TaskStatus,
} from "@/lib/types";

// ---- Auth API ----

export const authApi = {
  async login(email: string, password: string) {
    return apiClient.post<ApiResponse<{
      access_token: string;
      refresh_token: string;
      user: User;
    }>>("/auth/login", { email, password });
  },

  async register(nickname: string, email: string, password: string) {
    return apiClient.post<ApiResponse<{
      access_token: string;
      refresh_token: string;
      user: User;
    }>>("/auth/register", { nickname, email, password });
  },

  async refreshToken(refreshToken: string) {
    return apiClient.post<ApiResponse<{
      access_token: string;
      refresh_token: string;
    }>>("/auth/refresh", { refresh_token: refreshToken });
  },

  async getMe() {
    return apiClient.get<ApiResponse<User>>("/auth/me");
  },

  async resetPassword(email: string) {
    return apiClient.post<ApiResponse<{ sent: boolean; email: string }>>(
      "/auth/password-reset-request",
      { email },
    );
  },

  async setNewPassword(token: string, newPassword: string) {
    return apiClient.post<ApiResponse<{ message: string }>>(
      "/auth/password-reset",
      { token, new_password: newPassword },
    );
  },

  // 更新当前用户资料（对齐 OpenAPI 规范 PUT /auth/me）
  async updateProfile(data: { nickname?: string; bio?: string; avatar?: string }) {
    return apiClient.put<ApiResponse<User>>("/auth/me", data);
  },
};

// ---- Project API ----

export const projectApi = {
  async list() {
    return apiClient.get<ApiResponse<Project[]>>("/projects");
  },

  async getStats(projectId: string) {
    return apiClient.get<ApiResponse<{
      total: number;
      active: number;
      draft: number;
      total_words: number;
    }>>(`/projects/${projectId}/stats`);
  },

  async create(data: Partial<Project>) {
    return apiClient.post<ApiResponse<Project>>("/projects", data);
  },

  async getById(id: string) {
    return apiClient.get<ApiResponse<Project | null>>(`/projects/${id}`);
  },

  async update(id: string, data: Partial<Project>) {
    return apiClient.put<ApiResponse<Project>>(`/projects/${id}`, data);
  },

  async delete(id: string) {
    return apiClient.delete<ApiResponse<{ deleted: boolean; id: string }>>(
      `/projects/${id}`,
    );
  },

  // 保存草稿（对齐 OpenAPI 规范 PUT /projects/:id/draft）
  async saveDraft(id: string, data: Partial<Project>) {
    return apiClient.put<ApiResponse<Project>>(`/projects/${id}/draft`, data);
  },
};

// ---- Chapter API ----

export const chapterApi = {
  async getCurrent(projectId: string) {
    return apiClient.get<ApiResponse<Chapter | null>>(
      `/projects/${projectId}/chapters/current`,
    );
  },

  async list(projectId: string) {
    return apiClient.get<ApiResponse<Chapter[]>>(
      `/projects/${projectId}/chapters`,
    );
  },

  async create(data: Partial<Chapter>) {
    const projectId = data.project_id;
    if (!projectId) {
      throw new Error("创建章节需要提供 project_id");
    }
    return apiClient.post<ApiResponse<Chapter>>(
      `/projects/${projectId}/chapters`,
      data,
    );
  },

  async getById(projectId: string, id: string) {
    return apiClient.get<ApiResponse<Chapter | null>>(
      `/projects/${projectId}/chapters/${id}`,
    );
  },

  async update(projectId: string, id: string, data: Partial<Chapter>) {
    return apiClient.put<ApiResponse<Chapter>>(
      `/projects/${projectId}/chapters/${id}`,
      data,
    );
  },

  async delete(projectId: string, id: string) {
    return apiClient.delete<ApiResponse<null>>(
      `/projects/${projectId}/chapters/${id}`,
    );
  },

  async reorder(projectId: string, chapterNumbers: number[]) {
    return apiClient.post<ApiResponse<Chapter[]>>(
      `/projects/${projectId}/chapters/reorder`,
      { chapter_numbers: chapterNumbers },
    );
  },
};

// ---- Card API ----
// 注意：根据接口映射文档 4.4 节，抽卡需要以下参数：
// - chapter_id: 章节 ID
// - keep_card_ids[]: 保留的卡牌 ID 数组
// - draw_count: 抽卡数量（默认 3）
// - weights[]: 权重数组（可选）
// - mode: 生成模式（"single"|"dual"|"all"|"hybrid"）

export const cardApi = {
  async getPool(projectId: string, count?: number) {
    const params = count ? { count } : undefined;
    return apiClient.get<ApiResponse<CardPool[]>>(
      `/projects/${projectId}/cards/pool`,
      params,
    );
  },

  async drawCards(
    projectId: string,
    params: {
      chapter_id: string;
      keep_card_ids?: string[];
      draw_count?: number;
      weights?: number[];
      mode?: string;
    }
  ) {
    return apiClient.post<ApiResponse<DrawRecord>>(
      `/projects/${projectId}/cards/draw`,
      params,
    );
  },

  async redraw(
    projectId: string,
    chapterId: string,
    params?: {
      keep_card_ids?: string[];
      draw_count?: number;
    }
  ) {
    return apiClient.post<ApiResponse<DrawRecord>>(
      `/projects/${projectId}/chapters/${chapterId}/redraw`,
      params || {},
    );
  },

  async create(projectId: string, data: { name: string; type: string; rarity: string; description: string }) {
    return apiClient.post<ApiResponse<DrawRecord>>(
      `/projects/${projectId}/cards`,
      data,
    );
  },

  async retire(projectId: string, cardId: string) {
    return apiClient.post<ApiResponse<null>>(
      `/projects/${projectId}/cards/${cardId}/retire`,
      {},
    );
  },
};

// ---- Generation API ----
// 注意：根据接口映射文档 4.5 节，生成章节需要以下参数：
// - chapter_id: 章节 ID
// - card_ids[]: 卡牌 ID 数组
// - weights[]: 权重数组（可选）
// - mode: 生成模式（"single"|"dual"|"all"|"hybrid"）
// - creativity: 创意程度（1-10，可选）
// - word_count: 目标字数（500-5000，可选）

export const generationApi = {
  // 异步生成（立即返回 job_id）
  async generate(
    projectId: string,
    chapterId: string,
    params: {
      card_ids: string[];
      weights?: number[];
      mode?: string;
      creativity?: number;
      word_count?: number;
    }
  ) {
    return apiClient.post<ApiResponse<{ job_id: string; status: string }>>(
      `/generate/chapters/${chapterId}/generate?project_id=${projectId}`,
      params,
    );
  },

  // 查询异步任务状态（对齐后端 API: GET /generate/jobs/{job_id}）
  async getJobStatus(taskId: string) {
    return apiClient.get<ApiResponse<{
      status: string;
      progress?: { percent: number; stage: string };
      result?: { content: string; chapter_id: string };
      error?: string;
    }>>(
      `/generate/jobs/${taskId}`,
    );
  },

  // 取消任务（对齐 OpenAPI 规范）
  async cancelJob(taskId: string) {
    return apiClient.post<ApiResponse<{ status: string }>>(
      `/generate/jobs/${taskId}/cancel`,
      {},
    );
  },

  // 确认生成结果（向后兼容）
  async confirm(projectId: string, chapterId: string, nonce: string) {
    return apiClient.post<ApiResponse<{ confirmed: boolean; chapter_id: string; task_id?: string }>>(
      `/projects/${projectId}/chapters/${chapterId}/confirm`,
      { nonce },
    );
  },

  // 修订生成结果（向后兼容）
  async revise(projectId: string, chapterId: string, reason?: string) {
    return apiClient.post<ApiResponse<{ revised: boolean; chapter_id: string; suggestion?: string }>>(
      `/projects/${projectId}/chapters/${chapterId}/revise`,
      reason ? { reason } : {},
    );
  },

  // 获取生成历史（缺失端点-补）
  async getHistory(params?: { page?: number; page_size?: number }) {
    return apiClient.get<ApiResponse<{
      history: Array<{ task_id: string; chapter_id: string; status: string; created_at: string }>;
      total: number;
      page: number;
      page_size: number;
    }>>(
      `/generate/history`,
      params,
    );
  },
};

// ---- Vault API ----

export const vaultApi = {
  async getCharacters(projectId: string) {
    return apiClient.get<ApiResponse<VaultCharacter[]>>(
      `/projects/${projectId}/vault/characters`,
    );
  },

  async getCharacter(projectId: string, characterId: string) {
    return apiClient.get<ApiResponse<VaultCharacter>>(
      `/projects/${projectId}/vault/characters/${characterId}`,
    );
  },

  async createCharacter(projectId: string, data: Partial<VaultCharacter>) {
    return apiClient.post<ApiResponse<VaultCharacter>>(
      `/projects/${projectId}/vault/characters`,
      data,
    );
  },

  async updateCharacter(projectId: string, characterId: string, data: Partial<VaultCharacter>) {
    return apiClient.put<ApiResponse<VaultCharacter>>(
      `/projects/${projectId}/vault/characters/${characterId}`,
      data,
    );
  },

  async deleteCharacter(projectId: string, characterId: string) {
    return apiClient.delete<ApiResponse<null>>(
      `/projects/${projectId}/vault/characters/${characterId}`,
    );
  },

  async getTimeline(projectId: string) {
    return apiClient.get<ApiResponse<VaultTimeline[]>>(
      `/projects/${projectId}/vault/timeline`,
    );
  },

  async getPlotPromises(projectId: string) {
    return apiClient.get<ApiResponse<VaultPlotPromise[]>>(
      `/projects/${projectId}/vault/plot-promises`,
    );
  },

  async getWorld(projectId: string) {
    return apiClient.get<ApiResponse<VaultWorld[]>>(
      `/projects/${projectId}/vault/world`,
    );
  },

  async getSummary(projectId: string) {
    return apiClient.get<ApiResponse<VaultSummary>>(
      `/projects/${projectId}/vault/summary`,
    );
  },

  async fullReanalyze(projectId: string) {
    return apiClient.post<ApiResponse<{ status: string; task_id: string }>>(
      `/projects/${projectId}/vault/full-reanalyze`,
      {},
    );
  },

  // ---- Timeline CRUD ----

  async createTimelineEvent(projectId: string, data: Partial<VaultTimeline>) {
    return apiClient.post<ApiResponse<VaultTimeline>>(
      `/projects/${projectId}/vault/timeline`,
      data,
    );
  },

  async updateTimelineEvent(projectId: string, eventId: string, data: Partial<VaultTimeline>) {
    return apiClient.put<ApiResponse<VaultTimeline>>(
      `/projects/${projectId}/vault/timeline/${eventId}`,
      data,
    );
  },

  async deleteTimelineEvent(projectId: string, eventId: string) {
    return apiClient.delete<ApiResponse<null>>(
      `/projects/${projectId}/vault/timeline/${eventId}`,
    );
  },

  // ---- Plot Promise CRUD ----

  async createPlotPromise(projectId: string, data: Partial<VaultPlotPromise>) {
    return apiClient.post<ApiResponse<VaultPlotPromise>>(
      `/projects/${projectId}/vault/plot-promises`,
      data,
    );
  },

  async updatePlotPromise(projectId: string, promiseId: string, data: Partial<VaultPlotPromise>) {
    return apiClient.put<ApiResponse<VaultPlotPromise>>(
      `/projects/${projectId}/vault/plot-promises/${promiseId}`,
      data,
    );
  },

  async deletePlotPromise(projectId: string, promiseId: string) {
    return apiClient.delete<ApiResponse<null>>(
      `/projects/${projectId}/vault/plot-promises/${promiseId}`,
    );
  },

  // ---- World CRUD ----

  async createWorldEntry(projectId: string, data: Partial<VaultWorld>) {
    return apiClient.post<ApiResponse<VaultWorld>>(
      `/projects/${projectId}/vault/world`,
      data,
    );
  },

  async updateWorldEntry(projectId: string, entryId: string, data: Partial<VaultWorld>) {
    return apiClient.put<ApiResponse<VaultWorld>>(
      `/projects/${projectId}/vault/world/${entryId}`,
      data,
    );
  },

  async deleteWorldEntry(projectId: string, entryId: string) {
    return apiClient.delete<ApiResponse<null>>(
      `/projects/${projectId}/vault/world/${entryId}`,
    );
  },
};

// ---- Health API ----

export const healthApi = {
  async getAlerts(projectId: string) {
    return apiClient.get<ApiResponse<HealthAlert[]>>(
      `/projects/${projectId}/health`,
    );
  },

  async refreshCheck(projectId: string) {
    return apiClient.post<ApiResponse<HealthAlert[]>>(
      `/projects/${projectId}/health/refresh`,
    );
  },
};

// ---- System Health API ----

export const systemHealthApi = {
  async getStatus() {
    return apiClient.get<ApiResponse<SystemHealthStatus>>("/system/health");
  },
};

// ---- Settings API (D1) ----

export const settingsApi = {
  async get() {
    return apiClient.get<ApiResponse<UserSettings>>("/settings");
  },

  async update(data: Partial<UserSettings>) {
    return apiClient.put<ApiResponse<UserSettings>>("/settings", data);
  },

  async updateHealthMonitor(data: {
    r1_enabled?: boolean;
    r2_enabled?: boolean;
    r3_enabled?: boolean;
    anti_fatigue?: boolean;
  }) {
    return apiClient.patch<ApiResponse<Record<string, unknown>>>("/settings/health-monitor", data);
  },

  // getPhase4Review 已移除：后端没有对应的 GET 端点
  // 如需获取Phase4审核设置，请使用 updatePhase4Review 时返回完整设置

  async updatePhase4Review(data: { mode: "manual" | "auto" }) {
    return apiClient.patch<ApiResponse<Record<string, unknown>>>("/settings/phase4-review", data);
  },

  async exportData() {
    return apiClient.post<ApiResponse<{ export_url: string }>>("/settings/export", {});
  },

  async clearCache() {
    return apiClient.post<ApiResponse<{ cleared: boolean }>>("/settings/clear-cache", {});
  },

  async changePassword(oldPassword: string, newPassword: string) {
    return apiClient.post<ApiResponse<{ success: boolean }>>(
      "/settings/change-password",
      { old_password: oldPassword, new_password: newPassword },
    );
  },

  async getProfile() {
    return apiClient.get<ApiResponse<User>>("/settings/profile");
  },

  async updateProfile(data: { nickname?: string; bio?: string; avatar_url?: string }) {
    return apiClient.put<ApiResponse<User>>("/settings/profile", data);
  },

  // ---- Compatibility wrappers for old @/api settings interface ----

  async getSettings() {
    const res = await apiClient.get<ApiResponse<UserSettings>>("/settings");
    return {
      globalSettings: {
        theme: res.data.theme,
        language: res.data.language,
        autoSave: true,
        draftAutoConfirm: res.data.generation_preference?.auto_confirm ?? true,
        draftAutoConfirmSeconds: res.data.auto_save_interval ?? 6,
      },
    };
  },

  async updateGlobalSettings(globalSettings: Partial<{
    theme: string;
    language: string;
    autoSave: boolean;
    draftAutoConfirm: boolean;
    draftAutoConfirmSeconds: number;
  }>) {
    return apiClient.put<ApiResponse<UserSettings>>("/settings", globalSettings);
  },

  // updateProjectSettings 和 getProjectSettings 已移除
  // 后端没有项目级别的设置端点
};

// ---- Notifications API (D2) ----

export const notificationsApi = {
  async list(params?: { page?: number; page_size?: number; unread_only?: boolean }) {
    return apiClient.get<ApiResponse<{ items: Notification[]; total: number }>>("/notifications", params);
  },

  async markAsRead(notificationId: string) {
    return apiClient.post<ApiResponse<Notification>>(
      `/notifications/${notificationId}/read`,
      {},
    );
  },

  async markAllAsRead() {
    return apiClient.post<ApiResponse<{ updated: number }>>(
      "/notifications/read-all",
      {},
    );
  },

  async getUnreadCount() {
    return apiClient.get<ApiResponse<{ count: number }>>("/notifications/unread-count");
  },

  async deleteNotification(notificationId: string) {
    return apiClient.delete<ApiResponse<{ success: boolean }>>(`/notifications/${notificationId}`);
  },
};

// ---- Subscription API (D3) ----

export const subscriptionApi = {
  async getPlans() {
    return apiClient.get<ApiResponse<SubscriptionPlanDetails[]>>("/subscriptions/plans");
  },

  async createCheckout(plan: string, successUrl: string, cancelUrl: string) {
    return apiClient.post<ApiResponse<{ checkout_url: string; session_id: string }>>(
      "/subscriptions/create-checkout",
      { plan, success_url: successUrl, cancel_url: cancelUrl },
    );
  },

  async getCurrent() {
    return apiClient.get<ApiResponse<Subscription>>("/subscriptions/current");
  },

  // cancel 已移除：后端没有取消订阅端点

  // 获取支付记录（对齐 OpenAPI 规范 GET /subscriptions/payment-history）
  async getPaymentHistory(params?: { page?: number; page_size?: number }) {
    return apiClient.get<ApiResponse<Array<{
      id: string;
      amount: number;
      currency: string;
      status: string;
      created_at: string;
    }>>>(
      "/subscriptions/payment-history",
      params,
    );
  },
};

// ---- Secrets API (D4) ----
// 注意：根据接口映射文档 5.6 节，秘密矩阵 API 如下：
// - 列表：GET /api/v1/projects/:pid/secrets
// - 角色知识状态：GET /api/v1/projects/:pid/secrets/character/:name
// - 编辑秘密：PATCH /api/v1/projects/:pid/secrets/:sid

export const secretsApi = {
  async list(projectId: string) {
    return apiClient.get<ApiResponse<SecretMatrix[]>>(
      `/projects/${projectId}/secrets`,
    );
  },

  async getByCharacter(projectId: string, characterName: string) {
    return apiClient.get<ApiResponse<SecretMatrix>>(
      `/projects/${projectId}/secrets/character/${characterName}`,
    );
  },

  async update(projectId: string, secretId: string, data: Partial<SecretMatrix>) {
    return apiClient.patch<ApiResponse<SecretMatrix>>(
      `/projects/${projectId}/secrets/${secretId}`,
      data,
    );
  },
};

// ---- Templates API (D7) ----

export const templatesApi = {
  async list(params?: { genre?: string; official_only?: boolean }) {
    return apiClient.get<ApiResponse<Template[]>>("/templates", params);
  },

  async getById(templateId: string) {
    return apiClient.get<ApiResponse<Template>>(`/templates/${templateId}`);
  },

  async create(data: Partial<Template>) {
    return apiClient.post<ApiResponse<Template>>("/templates", data);
  },

  async update(templateId: string, data: Partial<Template>) {
    return apiClient.put<ApiResponse<Template>>(`/templates/${templateId}`, data);
  },

  async delete(templateId: string) {
    return apiClient.delete<ApiResponse<null>>(`/templates/${templateId}`);
  },

  async createProject(templateId: string, data?: { title?: string; author?: string }) {
    return apiClient.post<ApiResponse<{ project_id: string; title: string; status: string }>>(
      `/templates/${templateId}/create-project`,
      data || {},
    );
  },
};

// ---- Weave API (D8) ----
// list 端点：GET /weave/patterns
// apply 端点：POST /weave/apply（project_id 放在请求体中）
// 注意：后端没有 getById 端点，已移除

export const weaveApi = {
  async list() {
    return apiClient.get<ApiResponse<WeavePattern[]>>("/weave/patterns");
  },

  // getById 已移除：后端没有单个 pattern 详情端点
  // 如需获取 pattern 详情，可在前端从 list 结果中查找

  async apply(
    projectId: string,
    patternId: string,
    params?: Record<string, unknown>,
  ) {
    return apiClient.post<ApiResponse<{ applied: boolean; pattern_id: string }>>(
      `/weave/apply`,
      { project_id: projectId, pattern_id: patternId, ...params },
    );
  },

  // 获取编织建议（对齐 OpenAPI 规范 GET /weave/suggestions/{pid}）
  async getSuggestions(projectId: string) {
    return apiClient.get<ApiResponse<{
      suggestions: Array<{ pattern_id: string; chapter_id: string; suggestion: string; priority: string }>;
    }>>(`/weave/suggestions/${projectId}`);
  },

  // 编织分析（对齐 OpenAPI 规范 GET /weave/analyze/{pid}）
  async analyze(projectId: string) {
    return apiClient.get<ApiResponse<{
      total_patterns: number;
      applied_patterns: number;
      suggestions_count: number;
      analysis: string;
    }>>(`/weave/analyze/${projectId}`);
  },
};

// ---- Import API (D9) ----
// 注意：导入 API 的路径是 /projects/:pid/import，不是 /ingest/
// 后端目前只支持文本导入（POST /import，传递 text 参数）
// 文件上传功能待后端实现

export const importApi = {
  async createJob(projectId: string, data: { text?: string; source_type?: string }) {
    return apiClient.post<ApiResponse<{ job_id: string; status: string }>>(
      `/projects/${projectId}/import`,
      data,
    );
  },

  // 文件上传功能待后端实现，当前仅支持文本导入
  // 如需上传文件，请先读取文件内容为文本，再调用 createJob
  async uploadAndImport(
    projectId: string,
    file: File,
    _options?: {
      analyze_characters?: boolean;
      analyze_timeline?: boolean;
      analyze_commitments?: boolean;
      analyze_worldview?: boolean;
    }
  ): Promise<ApiResponse<{ job_id: string; status: string }>> {
    // 读取文件内容为文本
    const text = await file.text();
    return this.createJob(projectId, { text, source_type: 'file' });
  },

  async getJobStatus(projectId: string, jobId: string) {
    return apiClient.get<ApiResponse<{
      job_id: string;
      status: string;
      progress: number;
      current_phase?: string;
      result?: {
        characters_created: number;
        events_created: number;
        commitments_created: number;
        entries_created: number;
      };
      error?: string;
    }>>(`/projects/${projectId}/import/${jobId}`);
  },

  async runPhase1(projectId: string, jobId: string) {
    return apiClient.post<ApiResponse<{ status: string }>>(
      `/projects/${projectId}/import/${jobId}/phase1`,
      {},
    );
  },

  async runPhase2(projectId: string, jobId: string) {
    return apiClient.post<ApiResponse<{ status: string }>>(
      `/projects/${projectId}/import/${jobId}/phase2`,
      {},
    );
  },

  // 获取导入结果：使用 getJobStatus 返回的数据，无需单独的结果端点
  async getImportResult(projectId: string, jobId: string) {
    const res = await this.getJobStatus(projectId, jobId);
    return res.data;
  },

  async confirmImport(projectId: string, jobId: string) {
    return apiClient.post<ApiResponse<{ confirmed: boolean; job_id: string }>>(
      `/projects/${projectId}/import/${jobId}/confirm`,
      {},
    );
  },

  // 获取导入历史（对齐 OpenAPI 规范 GET /import）
  async getImportHistory(params?: { page?: number; page_size?: number }) {
    return apiClient.get<ApiResponse<{
      imports: Array<{ job_id: string; project_id: string; status: string; created_at: string }>;
      total: number;
      page: number;
      page_size: number;
    }>>("/import", params);
  },
};

// ---- Draft API (D10) ----
// 注意：后端没有独立的 draft 端点
// 保存草稿请直接使用 chapterApi.update()，传入 status: "draft"

// 已移除 draftApi，请使用 chapterApi.update 保存草稿

// ---- Chapter Suggestions/Agent API (D11) ----
// 根据接口映射文档 4.8 和 4.9 节
// 4.8: GET /api/v1/projects/:pid/chapters/:id/suggestions
//     响应: {suggestions: [{id, type, title, description, impact}]}
// 4.9: POST /api/v1/projects/:pid/chapters/:id/agent
//     请求: {command: string}
//     响应: {result: string, actions: [...]}

export interface ChapterSuggestion {
  id: string;
  type: string;
  title: string;
  description: string;
  impact: string;
}

export interface AgentResult {
  result: string;
  actions: unknown[];
}

export const chapterAgentApi = {
  async getSuggestions(projectId: string, chapterId: string) {
    return apiClient.get<ApiResponse<{ suggestions: ChapterSuggestion[] }>>(
      `/projects/${projectId}/chapters/${chapterId}/suggestions`,
    );
  },

  async runAgent(projectId: string, chapterId: string, command: string) {
    return apiClient.post<ApiResponse<AgentResult>>(
      `/projects/${projectId}/chapters/${chapterId}/agent`,
      { command },
    );
  },
};

// ---- Phase 4 Pending Reviews API (D12) ----

export const phase4Api = {
  async getPendingReviews() {
    return apiClient.get<ApiResponse<{ reviews: unknown[] }>>("/phase4/pending-reviews");
  },

  // approve 和 reject 已移除：后端没有对应的端点
  // 审核逻辑请直接使用 apply() 方法
  // approve(reviewId: string) {
  //   return apiClient.post("/phase4/apply", {
  //     suggestion_ids: [reviewId],
  //     action: "approve"
  //   });
  // },

  async getSuggestions(chapterId: string) {
    return apiClient.get<ApiResponse<{ suggestions: unknown[] }>>(
      `/phase4/chapters/${chapterId}/suggestions`,
    );
  },

  async apply(data: { suggestion_ids: number[]; chapter_id: number }) {
    return apiClient.post<ApiResponse<{ status: string; updated_content?: string }>>(
      "/phase4/apply",
      data,
    );
  },

  async getChapterTasks(chapterId: string) {
    return apiClient.get<ApiResponse<Phase4TaskStatus[]>>(
      `/phase4/chapters/${chapterId}/tasks`,
    );
  },

  async getProjectTasks(projectId: string) {
    return apiClient.get<ApiResponse<Phase4TaskStatus[]>>(
      `/phase4/projects/${projectId}/tasks`,
    );
  },

  async getTask(taskId: string) {
    return apiClient.get<ApiResponse<Phase4TaskStatus>>(
      `/phase4/tasks/${taskId}`,
    );
  },

  async retryTask(taskId: string) {
    return apiClient.post<ApiResponse<Phase4TaskStatus>>(
      `/phase4/tasks/${taskId}/retry`,
      {},
    );
  },
};

// ---- Draw History API (D13) ----

export const drawHistoryApi = {
  async list(projectId: string, params?: { page?: number; page_size?: number }) {
    return apiClient.get<ApiResponse<DrawHistory[]>>(
      `/projects/${projectId}/cards/draw-history`,
      params,
    );
  },

  async getById(projectId: string, drawId: string) {
    return apiClient.get<ApiResponse<DrawHistory>>(
      `/projects/${projectId}/cards/draw-history/${drawId}`,
    );
  },
};

// ---- Admin API (D14) ----

export const adminApi = {
  async getStats() {
    return apiClient.get<ApiResponse<AdminStats>>("/admin/stats");
  },

  async listUsers(params?: { page?: number; page_size?: number; search?: string }) {
    return apiClient.get<ApiResponse<AdminUser[]>>("/admin/users", params);
  },

  async listProjects(params?: { page?: number; page_size?: number; search?: string }) {
    return apiClient.get<ApiResponse<AdminProject[]>>("/admin/projects", params);
  },

  // ── LLM Config ──
  async getLlmConfig() {
    return apiClient.get<ApiResponse<{
      api_key_configured: boolean;
      api_base: string;
      model: string;
      api_keys: Array<{ id: string; name: string; prefix: string; enabled: boolean; created_at: string }>;
    }>>("/admin/llm-config");
  },

  async saveLlmConfig(data: { api_key?: string; api_base?: string; model?: string }) {
    return apiClient.post<ApiResponse<{ is_configured: boolean }>>("/admin/llm-config", data);
  },

  async testLlmConnection() {
    return apiClient.post<ApiResponse<{ success: boolean; message: string }>>("/admin/llm-config/test", {});
  },

  // 编辑用户（对齐 OpenAPI 规范 PATCH /admin/users/:id）
  async updateUser(userId: string, data: { role?: string; banned?: boolean }) {
    return apiClient.patch<ApiResponse<AdminUser>>(`/admin/users/${userId}`, data);
  },

  // LLM 用量统计（对齐 OpenAPI 规范 GET /admin/llm-usage）
  async getLlmUsage() {
    return apiClient.get<ApiResponse<{
      total_tokens: number;
      total_cost: number;
      by_provider: Record<string, number>;
      by_model: Record<string, number>;
      daily_usage: Array<{ date: string; tokens: number; cost: number }>;
    }>>("/admin/llm-usage");
  },
};
