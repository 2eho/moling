"use client";

import { useWorkspaceContext } from "@/contexts/WorkspaceContext";
import type { WorkspaceContextValue } from "@/contexts/WorkspaceContext";

/**
 * useWorkspace hook — 从 WorkspaceContext 读取工作台数据与操作方法。
 * 包含 null 检查，确保在 WorkspaceProvider 内使用。
 */
export function useWorkspace(): WorkspaceContextValue {
  return useWorkspaceContext();
}
