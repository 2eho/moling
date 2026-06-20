import { apiGet, apiPost, apiPut, apiDelete } from "./client";
import type {
  HealthCheckResp,
  Phase4Task,
  VaultCharacter,
  VaultTimeline,
  VaultForeshadowing,
  VaultWorldview,
  VaultSummary,
  VaultType,
  CardPoolItem,
  PaginatedResponse,
} from "@/lib/types/domain";

// ============ 健康监控 API ============
export function getProjectHealth(projectId: string): Promise<HealthCheckResp> {
  return apiGet<HealthCheckResp>(`/projects/${projectId}/health`);
}

export function refreshProjectHealth(projectId: string): Promise<HealthCheckResp> {
  return apiPost<HealthCheckResp>(`/projects/${projectId}/health/refresh`);
}

// ============ Phase 4 任务 API ============
export function getProjectPhase4Tasks(projectId: string): Promise<Phase4Task[]> {
  return apiGet<Phase4Task[]>(`/phase4/projects/${projectId}/tasks`);
}

export function getPhase4Task(taskId: string): Promise<Phase4Task> {
  return apiGet<Phase4Task>(`/phase4/tasks/${taskId}`);
}

export function getChapterPhase4Tasks(chapterId: string): Promise<Phase4Task[]> {
  return apiGet<Phase4Task[]>(`/phase4/chapters/${chapterId}/tasks`);
}

// ============ Vault 四库 API ============
export function getVaultCharacters(
  projectId: string,
  params?: { page?: number; page_size?: number; search?: string }
): Promise<PaginatedResponse<VaultCharacter>> {
  const searchParams = new URLSearchParams();
  if (params?.page) searchParams.set("page", String(params.page));
  if (params?.page_size) searchParams.set("page_size", String(params.page_size));
  if (params?.search) searchParams.set("search", params.search);
  const qs = searchParams.toString();
  return apiGet<PaginatedResponse<VaultCharacter>>(
    `/projects/${projectId}/vault/characters${qs ? `?${qs}` : ""}`
  );
}

export function getVaultTimeline(
  projectId: string,
  params?: { page?: number; page_size?: number }
): Promise<PaginatedResponse<VaultTimeline>> {
  const searchParams = new URLSearchParams();
  if (params?.page) searchParams.set("page", String(params.page));
  if (params?.page_size) searchParams.set("page_size", String(params.page_size));
  const qs = searchParams.toString();
  return apiGet<PaginatedResponse<VaultTimeline>>(
    `/projects/${projectId}/vault/timeline${qs ? `?${qs}` : ""}`
  );
}

export function getVaultForeshadowing(
  projectId: string,
  params?: { page?: number; page_size?: number; status?: string }
): Promise<PaginatedResponse<VaultForeshadowing>> {
  const searchParams = new URLSearchParams();
  if (params?.page) searchParams.set("page", String(params.page));
  if (params?.page_size) searchParams.set("page_size", String(params.page_size));
  if (params?.status) searchParams.set("status", params.status);
  const qs = searchParams.toString();
  return apiGet<PaginatedResponse<VaultForeshadowing>>(
    `/projects/${projectId}/vault/foreshadowing${qs ? `?${qs}` : ""}`
  );
}

export function getVaultWorldview(
  projectId: string,
  params?: { page?: number; page_size?: number; category?: string }
): Promise<PaginatedResponse<VaultWorldview>> {
  const searchParams = new URLSearchParams();
  if (params?.page) searchParams.set("page", String(params.page));
  if (params?.page_size) searchParams.set("page_size", String(params.page_size));
  if (params?.category) searchParams.set("category", params.category);
  const qs = searchParams.toString();
  return apiGet<PaginatedResponse<VaultWorldview>>(
    `/projects/${projectId}/vault/worldview${qs ? `?${qs}` : ""}`
  );
}

export function getVaultSummary(projectId: string): Promise<VaultSummary> {
  return apiGet<VaultSummary>(`/projects/${projectId}/vault/summary`);
}

// ============ Card Pool API ============
export function getCardPool(
  projectId: string,
  params?: { page?: number; page_size?: number; retired?: string }
): Promise<PaginatedResponse<CardPoolItem>> {
  const searchParams = new URLSearchParams();
  if (params?.page) searchParams.set("page", String(params.page));
  if (params?.page_size) searchParams.set("page_size", String(params.page_size));
  if (params?.retired) searchParams.set("retired", params.retired);
  const qs = searchParams.toString();
  return apiGet<PaginatedResponse<CardPoolItem>>(
    `/projects/${projectId}/cards${qs ? `?${qs}` : ""}`
  );
}

export function retireCard(projectId: string, cardId: string, reason: string): Promise<CardPoolItem> {
  return apiPost<CardPoolItem>(`/projects/${projectId}/cards/${cardId}/retire`, { reason });
}
