// Settings 相关 API
import { api } from './client';
import type {
  UserSettings,
  ChangePasswordRequest,
  UpdateProfileRequest,
  User,
} from './types';

// 获取用户设置
export async function getSettings(): Promise<UserSettings> {
  return api.get<UserSettings>('/settings');
}

// 更新用户设置
export async function updateSettings(
  settings: Partial<UserSettings>
): Promise<UserSettings> {
  return api.put<UserSettings>('/settings', settings);
}

// 更新全局设置
export async function updateGlobalSettings(
  globalSettings: Partial<UserSettings['globalSettings']>
): Promise<UserSettings> {
  return api.patch<UserSettings>('/settings/global', globalSettings);
}

// 更新项目设置
export async function updateProjectSettings(
  projectId: string,
  projectSettings: any
): Promise<UserSettings> {
  return api.patch<UserSettings>(
    `/settings/project/${projectId}`,
    projectSettings
  );
}

// 修改密码
export async function changePassword(
  request: ChangePasswordRequest
): Promise<{ success: boolean }> {
  return api.post<{ success: boolean }>('/settings/password', request);
}

// 更新个人资料
export async function updateProfile(
  request: UpdateProfileRequest
): Promise<User> {
  return api.put<User>('/settings/profile', request);
}

// 获取项目级设置
export async function getProjectSettings(
  projectId: string
): Promise<Record<string, any>> {
  return api.get<Record<string, any>>(`/settings/project/${projectId}`);
}
