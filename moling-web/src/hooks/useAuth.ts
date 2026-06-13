"use client";

import { useAuth as useAuthFromContext } from "@/contexts/AuthContext";
import type { AuthContextValue } from "@/contexts/AuthContext";

/**
 * useAuth hook — 从 AuthContext 读取认证状态与方法。
 * 包含 null 检查，确保在 AuthProvider 内使用。
 */
export function useAuth(): AuthContextValue {
  return useAuthFromContext();
}
