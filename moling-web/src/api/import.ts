// Import 相关 API
import { api } from './client';
import type { ImportRequest, ImportProgress } from './types';

// 上传文件并开始导入
export async function uploadAndImport(
  projectId: string,
  file: File,
  options?: {
    analyzeCharacters?: boolean;
    analyzeTimeline?: boolean;
    analyzeCommitments?: boolean;
    analyzeWorldview?: boolean;
  }
): Promise<{ taskId: string }> {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('projectId', projectId);

  if (options) {
    Object.entries(options).forEach(([key, value]) => {
      if (value !== undefined) {
        formData.append(key, value.toString());
      }
    });
  }

  const token = localStorage.getItem('moling_token');
  const headers: Record<string, string> = {};
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const response = await fetch(
    `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:3001/api'}/import/upload`,
    {
      method: 'POST',
      headers,
      body: formData,
    }
  );

  if (!response.ok) {
    const errorData = await response.json().catch(() => null);
    throw new Error(errorData?.message || 'Upload failed');
  }

  const data = await response.json();
  return data.data;
}

// 开始导入（已上传文件）
export async function startImport(
  request: ImportRequest
): Promise<{ taskId: string }> {
  return api.post<{ taskId: string }>('/import/start', request);
}

// 轮询导入进度
export async function getImportProgress(
  taskId: string
): Promise<ImportProgress> {
  return api.get<ImportProgress>(`/import/${taskId}/progress`);
}

// 获取导入结果
export async function getImportResult(
  taskId: string
): Promise<ImportProgress['result']> {
  return api.get<ImportProgress['result']>(`/import/${taskId}/result`);
}

// 取消导入
export async function cancelImport(
  taskId: string
): Promise<{ success: boolean }> {
  return api.post<{ success: boolean }>(`/import/${taskId}/cancel`);
}

// 获取导入历史
export async function getImportHistory(
  projectId: string
): Promise<Array<{ id: string; fileName: string; status: string; createdAt: string }>> {
  return api.get(`/projects/${projectId}/import-history`);
}
