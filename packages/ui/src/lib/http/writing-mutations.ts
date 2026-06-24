"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { env } from "@/lib/env";
import { apiPost } from "@/lib/http/client";
import { useWritingStore } from "@/stores/useWritingStore";

// ============================================================
// 墨灵 Vibe Writing — TanStack Query Mutation Hooks
// 通过 NEXT_PUBLIC_MOCK_ENABLED 环境变量控制 mock / 真实 API 切换
// ============================================================

/** Mock 延迟（模拟网络请求） */
async function mockDelay(): Promise<void> {
  await new Promise((r) => setTimeout(r, 1200));
}

// ---- Mock 实现 ----

/** Mock: 提交选项选择 (A/B/C) */
async function mockSelectOption(optionId: string) {
  await mockDelay();
  return { success: true, optionId };
}

/** Mock: 提交自定义输入 (D) */
async function mockSubmitCustom(input: string) {
  await mockDelay();
  return { success: true, input };
}

/** Mock: 重新生成选项 */
async function mockGenerateOptions() {
  await mockDelay();
  return { success: true };
}

// ---- Mutation Hooks ----

/** 提交选项选择 (A/B/C) */
export function useSelectOptionMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (optionId: string) =>
      env.mockEnabled
        ? mockSelectOption(optionId)
        : apiPost("/api/writing/select-option", { optionId }),
    onSuccess: () => {
      useWritingStore.setState({ isGenerating: false });
      queryClient.invalidateQueries({ queryKey: ["writing", "generation"] });
    },
    onError: () => {
      useWritingStore.setState({ isGenerating: false });
    },
  });
}

/** 提交自定义输入 (D) */
export function useSubmitCustomMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (input: string) =>
      env.mockEnabled ? mockSubmitCustom(input) : apiPost("/api/writing/submit-custom", { input }),
    onSuccess: () => {
      useWritingStore.setState({ isGenerating: false });
      queryClient.invalidateQueries({ queryKey: ["writing", "generation"] });
    },
    onError: () => {
      useWritingStore.setState({ isGenerating: false });
    },
  });
}

/** 重新生成选项 */
export function useGenerateOptionsMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async () =>
      env.mockEnabled ? mockGenerateOptions() : apiPost("/api/writing/generate-options"),
    onSuccess: () => {
      useWritingStore.setState({ isGenerating: false });
      queryClient.invalidateQueries({ queryKey: ["writing", "options"] });
    },
    onError: () => {
      useWritingStore.setState({ isGenerating: false });
    },
  });
}
