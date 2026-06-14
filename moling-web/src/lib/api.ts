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
};

// ---- Card API ----
// 注意：根据接口映射文档 4.4 节，抽卡需要以下参数：
// - chapter_id: 章节 ID
// - keep_card_ids[]: 保留的卡牌 ID 数组
// - draw_count: 抽卡数量（默认 3）
// - weights[]: 权重数组（可选）
// - mode: 生成模式（"single"|"dual"|"all"|"hybrid"）

export const cardApi = {
  async getPool(projectId: string) {
    return apiClient.get<ApiResponse<CardPool[]>>(
      `/projects/${projectId}/cards/pool`,
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
    return apiClient.post<ApiResponse<GenerationTask>>(
      `/projects/${projectId}/chapters/${chapterId}/generate`,
      params,
    );
  },

  async getStatus(taskId: string) {
    return apiClient.get<ApiResponse<GenerationTask>>(
      `/generation/${taskId}/status`,
    );
  },

  async cancel(taskId: string) {
    return apiClient.post<ApiResponse<{ cancelled: boolean; task_id: string }>>(
      `/generation/${taskId}/cancel`,
    );
  },

  async confirm(projectId: string, chapterId: string) {
    return apiClient.post<ApiResponse<{ confirmed: boolean; chapter_id: string }>>(
      `/projects/${projectId}/chapters/${chapterId}/confirm`,
    );
  },

  async revise(projectId: string, chapterId: string) {
    return apiClient.post<ApiResponse<{ revised: boolean; chapter_id: string }>>(
      `/projects/${projectId}/chapters/${chapterId}/revise`,
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
      `/projects/${projectId}/health/alerts`,
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

  async getHealthMonitor() {
    return apiClient.get<ApiResponse<Record<string, unknown>>>("/settings/health-monitor");
  },

  async getPhase4Review() {
    return apiClient.get<ApiResponse<Record<string, unknown>>>("/settings/phase4-review");
  },

  async exportData() {
    return apiClient.post<ApiResponse<{ export_url: string }>>("/settings/export", {});
  },

  async clearCache() {
    return apiClient.post<ApiResponse<{ cleared: boolean }>>("/settings/clear-cache", {});
  },

  async changePassword(oldPassword: string, newPassword: string) {
    return apiClient.post<ApiResponse<{ success: boolean }>>(
      "/settings/password",
      { old_password: oldPassword, new_password: newPassword },
    );
  },

  async updateProfile(data: { nickname?: string; bio?: string; avatar_url?: string }) {
    return apiClient.put<ApiResponse<User>>("/auth/me", data);
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

  async updateProjectSettings(projectId: string, projectSettings: {
    aiSpeed?: number;
    writingStyle?: number;
    notificationEnabled?: boolean;
  }) {
    return apiClient.patch<ApiResponse<UserSettings>>(`/settings/project/${projectId}`, projectSettings);
  },

  async getProjectSettings(projectId: string) {
    return apiClient.get<ApiResponse<Record<string, unknown>>>(`/settings/project/${projectId}`);
  },
};

// ---- Notifications API (D2) ----

export const notificationsApi = {
  async list(params?: { page?: number; page_size?: number; unread_only?: boolean }) {
    return apiClient.get<ApiResponse<Notification[]>>("/notifications", params);
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

  async deleteAllRead() {
    return apiClient.delete<ApiResponse<{ success: boolean }>>("/notifications/delete-read");
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

  async cancel() {
    return apiClient.post<ApiResponse<Subscription>>("/subscriptions/cancel", {});
  },
};

// ---- Secrets API (D4) ----

export const secretsApi = {
  async list(projectId: string) {
    return apiClient.get<ApiResponse<SecretMatrix[]>>(
      `/projects/${projectId}/secrets`,
    );
  },

  async getByCharacter(projectId: string, characterId: string) {
    return apiClient.get<ApiResponse<SecretMatrix>>(
      `/projects/${projectId}/secrets/character/${characterId}`,
    );
  },

  async update(projectId: string, characterId: string, data: Partial<SecretMatrix>) {
    return apiClient.put<ApiResponse<SecretMatrix>>(
      `/projects/${projectId}/secrets/character/${characterId}`,
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

  async delete(templateId: string) {
    return apiClient.delete<ApiResponse<null>>(`/templates/${templateId}`);
  },
};

// ---- Weave API (D8) ----

export const weaveApi = {
  async list() {
    return apiClient.get<ApiResponse<WeavePattern[]>>("/weave/patterns");
  },

  async getById(patternId: string) {
    return apiClient.get<ApiResponse<WeavePattern>>(`/weave/patterns/${patternId}`);
  },

  async apply(projectId: string, patternId: string, params?: Record<string, unknown>) {
    return apiClient.post<ApiResponse<{ applied: boolean; pattern_id: string }>>(
      `/projects/${projectId}/weave/apply`,
      { pattern_id: patternId, ...params },
    );
  },
};

// ---- Import API (D9) ----
// 注意：导入 API 的路径是 /projects/:pid/import，不是 /ingest/

export const importApi = {
  async createJob(projectId: string, data: { text?: string; source_type?: string }) {
    return apiClient.post<ApiResponse<{ job_id: string; status: string }>>(
      `/projects/${projectId}/import`,
      data,
    );
  },

  async uploadAndImport(
    projectId: string,
    file: File,
    options?: {
      analyze_characters?: boolean;
      analyze_timeline?: boolean;
      analyze_commitments?: boolean;
      analyze_worldview?: boolean;
    }
  ): Promise<{ job_id: string; status: string }> {
    const formData = new FormData();
    formData.append('file', file);
    
    if (options) {
      Object.entries(options).forEach(([key, value]) => {
        if (value !== undefined) {
          formData.append(key, value.toString());
        }
      });
    }

    const token = typeof window !== 'undefined' ? localStorage.getItem('moling_token') : null;
    const headers: Record<string, string> = {};
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL
      ?? process.env.NEXT_PUBLIC_API_URL
      ?? 'http://localhost:8000/api/v1';
    
    const response = await fetch(`${baseUrl}/projects/${projectId}/import/upload`, {
      method: 'POST',
      headers,
      body: formData,
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => null);
      throw new Error(errorData?.message || 'Upload failed');
    }

    const result = await response.json();
    return result.data;
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

  async getImportResult(projectId: string, jobId: string) {
    return apiClient.get<ApiResponse<{
      characters_created: number;
      events_created: number;
      commitments_created: number;
      entries_created: number;
    }>>(`/projects/${projectId}/import/${jobId}/result`);
  },

  async confirmImport(projectId: string, jobId: string) {
    return apiClient.post<ApiResponse<{ confirmed: boolean; job_id: string }>>(
      `/projects/${projectId}/import/${jobId}/confirm`,
      {},
    );
  },

  async getImportHistory(projectId: string) {
    const res = await apiClient.get<ApiResponse<Array<{
      id: string;
      file_name: string;
      status: string;
      created_at: string;
    }>>>(`/projects/${projectId}/import-history`);
    return res.data;
  },
};

// ---- Save Draft API (D10) ----

export const draftApi = {
  async save(projectId: string, chapterId: string, content: string) {
    return apiClient.post<ApiResponse<{ saved: boolean; draft_id: string }>>(
      `/projects/${projectId}/chapters/${chapterId}/draft`,
      { content },
    );
  },

  async get(projectId: string, chapterId: string) {
    return apiClient.get<ApiResponse<{ content: string; updated_at: string }>>(
      `/projects/${projectId}/chapters/${chapterId}/draft`,
    );
  },
};

// ---- Chapter Suggestions/Agent API (D11) ----

export const chapterAgentApi = {
  async getSuggestions(projectId: string, chapterId: string) {
    return apiClient.get<ApiResponse<{ suggestions: string[] }>>(
      `/projects/${projectId}/chapters/${chapterId}/suggestions`,
    );
  },

  async runAgent(projectId: string, chapterId: string, instruction: string) {
    return apiClient.post<ApiResponse<{ task_id: string }>>(
      `/projects/${projectId}/chapters/${chapterId}/agent`,
      { instruction },
    );
  },
};

// ---- Phase 4 Pending Reviews API (D12) ----

export const phase4Api = {
  async getPendingReviews() {
    return apiClient.get<ApiResponse<{ reviews: unknown[] }>>("/phase4/pending-reviews");
  },

  async approve(reviewId: string) {
    return apiClient.post<ApiResponse<{ approved: boolean }>>(
      `/phase4/reviews/${reviewId}/approve`,
      {},
    );
  },

  async reject(reviewId: string, reason: string) {
    return apiClient.post<ApiResponse<{ rejected: boolean }>>(
      `/phase4/reviews/${reviewId}/reject`,
      { reason },
    );
  },
};

// ---- Draw History API (D13) ----

export const drawHistoryApi = {
  async list(projectId: string, params?: { page?: number; page_size?: number }) {
    return apiClient.get<ApiResponse<DrawHistory[]>>(
      `/projects/${projectId}/draw-history`,
      params,
    );
  },

  async getById(projectId: string, drawId: string) {
    return apiClient.get<ApiResponse<DrawHistory>>(
      `/projects/${projectId}/draw-history/${drawId}`,
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

  async updateUser(userId: string, data: Partial<AdminUser>) {
    return apiClient.put<ApiResponse<AdminUser>>(`/admin/users/${userId}`, data);
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

  async getLlmPools() {
    return apiClient.get<ApiResponse<{
      pro_pool: { total: number; used: number; available: number; status: "healthy" | "degraded" | "down" };
      flash_pool: { total: number; used: number; available: number; status: "healthy" | "degraded" | "down" };
    }>>("/admin/llm-config/pools");
  },

  async addApiKey(data: { name: string; key: string }) {
    return apiClient.post<ApiResponse<{ id: string; prefix: string }>>("/admin/llm-config/keys", data);
  },

  async deleteApiKey(keyId: string) {
    return apiClient.delete<ApiResponse<{ deleted: boolean }>>(`/admin/llm-config/keys/${keyId}`);
  },

  async toggleApiKey(keyId: string, enabled: boolean) {
    return apiClient.patch<ApiResponse<{ enabled: boolean }>>(`/admin/llm-config/keys/${keyId}`, { enabled });
  },
};
