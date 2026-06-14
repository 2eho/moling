// Vault 四库相关 API
import { api } from './client';
import type {
  Character,
  CreateCharacterRequest,
  TimelineEvent,
  Commitment,
  WorldviewEntry,
} from './types';

// ==================== 角色库 ====================

// 获取项目的所有角色
export async function getCharacters(projectId: string): Promise<Character[]> {
  return api.get<Character[]>(`/projects/${projectId}/characters`);
}

// 获取单个角色
export async function getCharacter(characterId: string): Promise<Character> {
  return api.get<Character>(`/characters/${characterId}`);
}

// 创建角色
export async function createCharacter(
  projectId: string,
  request: CreateCharacterRequest
): Promise<Character> {
  return api.post<Character>(`/projects/${projectId}/characters`, request);
}

// 更新角色
export async function updateCharacter(
  characterId: string,
  request: Partial<CreateCharacterRequest>
): Promise<Character> {
  return api.put<Character>(`/characters/${characterId}`, request);
}

// 删除角色
export async function deleteCharacter(characterId: string): Promise<{ success: boolean }> {
  return api.delete<{ success: boolean }>(`/characters/${characterId}`);
}

// ==================== 时间线库 ====================

// 获取项目的时间线事件
export async function getTimelineEvents(projectId: string): Promise<TimelineEvent[]> {
  return api.get<TimelineEvent[]>(`/projects/${projectId}/timeline`);
}

// 创建时间线事件
export async function createTimelineEvent(
  projectId: string,
  event: Omit<TimelineEvent, 'id' | 'projectId'>
): Promise<TimelineEvent> {
  return api.post<TimelineEvent>(`/projects/${projectId}/timeline`, event);
}

// 更新时间线事件
export async function updateTimelineEvent(
  eventId: string,
  event: Partial<TimelineEvent>
): Promise<TimelineEvent> {
  return api.put<TimelineEvent>(`/timeline/${eventId}`, event);
}

// 删除时间线事件
export async function deleteTimelineEvent(eventId: string): Promise<{ success: boolean }> {
  return api.delete<{ success: boolean }>(`/timeline/${eventId}`);
}

// ==================== 剧情承诺库 ====================

// 获取项目的剧情承诺
export async function getCommitments(projectId: string): Promise<Commitment[]> {
  return api.get<Commitment[]>(`/projects/${projectId}/commitments`);
}

// 创建剧情承诺
export async function createCommitment(
  projectId: string,
  commitment: Omit<Commitment, 'id' | 'projectId'>
): Promise<Commitment> {
  return api.post<Commitment>(`/projects/${projectId}/commitments`, commitment);
}

// 更新剧情承诺
export async function updateCommitment(
  commitmentId: string,
  commitment: Partial<Commitment>
): Promise<Commitment> {
  return api.put<Commitment>(`/commitments/${commitmentId}`, commitment);
}

// 删除剧情承诺
export async function deleteCommitment(commitmentId: string): Promise<{ success: boolean }> {
  return api.delete<{ success: boolean }>(`/commitments/${commitmentId}`);
}

// ==================== 世界观库 ====================

// 获取项目的世界观条目
export async function getWorldviewEntries(projectId: string): Promise<WorldviewEntry[]> {
  return api.get<WorldviewEntry[]>(`/projects/${projectId}/worldview`);
}

// 创建世界观条目
export async function createWorldviewEntry(
  projectId: string,
  entry: Omit<WorldviewEntry, 'id' | 'projectId'>
): Promise<WorldviewEntry> {
  return api.post<WorldviewEntry>(`/projects/${projectId}/worldview`, entry);
}

// 更新世界观条目
export async function updateWorldviewEntry(
  entryId: string,
  entry: Partial<WorldviewEntry>
): Promise<WorldviewEntry> {
  return api.put<WorldviewEntry>(`/worldview/${entryId}`, entry);
}

// 删除世界观条目
export async function deleteWorldviewEntry(entryId: string): Promise<{ success: boolean }> {
  return api.delete<{ success: boolean }>(`/worldview/${entryId}`);
}
