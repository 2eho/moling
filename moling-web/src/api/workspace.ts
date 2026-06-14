// Workspace 相关 API
import { api } from './client';
import type {
  CardDirection,
  GenerateRequest,
  GenerateResponse,
  GenerationProgress,
  ConfirmRequest,
  ReviseRequest,
  Chapter,
} from './types';

// 获取章节详情
export async function getChapter(chapterId: string): Promise<Chapter> {
  return api.get<Chapter>(`/chapters/${chapterId}`);
}

// 获取灵感卡牌
export async function getCards(chapterId: string): Promise<CardDirection[]> {
  return api.get<CardDirection[]>(`/chapters/${chapterId}/cards`);
}

// 生成章节内容
export async function generateChapter(
  request: GenerateRequest
): Promise<GenerateResponse> {
  return api.post<GenerateResponse>('/generate', request);
}

// 轮询生成进度
export async function getGenerationProgress(
  taskId: string
): Promise<GenerationProgress> {
  return api.get<GenerationProgress>(`/generate/${taskId}/progress`);
}

// 确认收纳（Confirm API）
export async function confirmChapter(
  request: ConfirmRequest
): Promise<{ success: boolean }> {
  return api.post<{ success: boolean }>('/workspace/confirm', request);
}

// 拒稿修订（Revise API）
export async function reviseChapter(
  request: ReviseRequest
): Promise<{ success: boolean }> {
  return api.post<{ success: boolean }>('/workspace/revise', request);
}

// 取消生成（Cancel API）
export async function cancelGeneration(
  taskId: string
): Promise<{ success: boolean }> {
  return api.post<{ success: boolean }>(`/generate/${taskId}/cancel`);
}

// 获取健康告警
export async function getHealthAlerts(
  projectId: string
): Promise<Array<{ type: string; message: string; severity: 'info' | 'warning' | 'error' }>> {
  return api.get(`/projects/${projectId}/health`);
}

// 保存草稿
export async function saveDraft(
  chapterId: string,
  content: string
): Promise<{ success: boolean }> {
  return api.put<{ success: boolean }>(`/chapters/${chapterId}/draft`, { content });
}

// 获取建议
export async function getSuggestions(
  chapterId: string
): Promise<Array<{ id: string; text: string }>> {
  return api.get(`/chapters/${chapterId}/suggestions`);
}
