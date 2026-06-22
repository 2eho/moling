import { apiGet, apiPost, apiPut, apiDelete } from "./client";
import { API_ENDPOINTS } from "@/lib/constants";
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
  return apiGet<HealthCheckResp>(API_ENDPOINTS.PROJECTS.HEALTH(projectId));
}

export function refreshProjectHealth(projectId: string): Promise<HealthCheckResp> {
  return apiPost<HealthCheckResp>(API_ENDPOINTS.PROJECTS.HEALTH_REFRESH(projectId));
}

// ============ Phase 4 任务 API ============
export function getProjectPhase4Tasks(projectId: string): Promise<Phase4Task[]> {
  return apiGet<Phase4Task[]>(API_ENDPOINTS.PHASE4.PROJECT_TASKS(projectId));
}

export function getPhase4Task(taskId: string): Promise<Phase4Task> {
  return apiGet<Phase4Task>(API_ENDPOINTS.PHASE4.TASK_DETAIL(taskId));
}

export function getChapterPhase4Tasks(chapterId: string): Promise<Phase4Task[]> {
  return apiGet<Phase4Task[]>(API_ENDPOINTS.PHASE4.CHAPTER_TASKS(chapterId));
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
    `${API_ENDPOINTS.VAULT.CHARACTERS(projectId)}${qs ? `?${qs}` : ""}`
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
    `${API_ENDPOINTS.VAULT.TIMELINE(projectId)}${qs ? `?${qs}` : ""}`
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
    `${API_ENDPOINTS.VAULT.FORESHADOWING(projectId)}${qs ? `?${qs}` : ""}`
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
    `${API_ENDPOINTS.VAULT.WORLDVIEW(projectId)}${qs ? `?${qs}` : ""}`
  );
}

export function getVaultSummary(projectId: string): Promise<VaultSummary> {
  return apiGet<VaultSummary>(API_ENDPOINTS.VAULT.SUMMARY(projectId));
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
    `${API_ENDPOINTS.CARDS.LIST(projectId)}${qs ? `?${qs}` : ""}`
  );
}

export function retireCard(projectId: string, cardId: string, reason: string): Promise<CardPoolItem> {
  return apiPost<CardPoolItem>(API_ENDPOINTS.CARDS.RETIRE(projectId, cardId), { reason });
}
