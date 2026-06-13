"use client";

import { useProjectContext } from "@/contexts/ProjectContext";
import type { ProjectContextValue } from "@/contexts/ProjectContext";

/**
 * useProjects hook — 从 ProjectContext 读取项目数据和操作方法。
 * 包含 null 检查，确保在 ProjectProvider 内使用。
 */
export function useProjects(): ProjectContextValue {
  return useProjectContext();
}
