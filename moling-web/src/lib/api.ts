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

export const cardApi = {
  async getPool(projectId: string) {
    return apiClient.get<ApiResponse<CardPool[]>>(
      `/projects/${projectId}/cards/pool`,
    );
  },

  async drawCards(
    projectId: string,
    cardIds: string[],
    weights: number[],
    mode: string,
  ) {
    return apiClient.post<ApiResponse<DrawRecord>>(
      `/projects/${projectId}/cards/draw`,
      { card_ids: cardIds, weights, mode },
    );
  },

  async redraw(projectId: string, chapterId: string) {
    return apiClient.post<ApiResponse<DrawRecord>>(
      `/projects/${projectId}/chapters/${chapterId}/redraw`,
    );
  },
};

// ---- Generation API ----

export const generationApi = {
  async generate(projectId: string, chapterId: string, cardIds: string[]) {
    return apiClient.post<ApiResponse<GenerationTask>>(
      `/projects/${projectId}/chapters/${chapterId}/generate`,
      { card_ids: cardIds },
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

export const importApi = {
  async createJob(projectId: string, data: { source_type: string; source_url?: string; file_path?: string }) {
    return apiClient.post<ApiResponse<{ job_id: string; status: string }>>(
      `/ingest/projects/${projectId}/jobs`,
      data,
    );
  },

  async getJob(projectId: string, jobId: string) {
    return apiClient.get<ApiResponse<{ job_id: string; status: string; progress: number }>>(
      `/ingest/projects/${projectId}/jobs/${jobId}`,
    );
  },

  async listJobs(projectId: string) {
    return apiClient.get<ApiResponse<{ jobs: unknown[] }>>(
      `/ingest/projects/${projectId}/jobs`,
    );
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
};
