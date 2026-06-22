import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useWritingStore } from "@/stores/useWritingStore";
import {
  useSelectOptionMutation,
  useSubmitCustomMutation,
  useGenerateOptionsMutation,
} from "../writing-mutations";

// Mock env to enable mock mode
vi.mock("@/lib/env", () => ({
  env: {
    mockEnabled: true,
    apiBaseUrl: "/api/v1",
  },
}));

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
  return function Wrapper({ children }: { children: React.ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>
        {children}
      </QueryClientProvider>
    );
  };
}

describe("writing-mutations", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    // Reset the writing store
    useWritingStore.setState({ isGenerating: false });

    // Mock fetch for any potential API calls
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ success: true }),
    });
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  describe("useSelectOptionMutation", () => {
    it("returns a mutation hook", () => {
      const { result } = renderHook(() => useSelectOptionMutation(), {
        wrapper: createWrapper(),
      });

      expect(result.current).toBeDefined();
      expect(typeof result.current.mutate).toBe("function");
      expect(typeof result.current.mutateAsync).toBe("function");
    });

    it("mutation resolves after mock delay", async () => {
      const { result } = renderHook(() => useSelectOptionMutation(), {
        wrapper: createWrapper(),
      });

      let data: unknown;
      act(() => {
        result.current.mutate("opt-a", {
          onSuccess: (d) => { data = d; },
        });
      });

      // Fast-forward through the mock delay
      await act(async () => {
        vi.advanceTimersByTime(1200);
      });

      await waitFor(() => {
        expect(data).toEqual({ success: true, optionId: "opt-a" });
      });
    });

    it("resets isGenerating on success", async () => {
      useWritingStore.setState({ isGenerating: true });

      const { result } = renderHook(() => useSelectOptionMutation(), {
        wrapper: createWrapper(),
      });

      act(() => {
        result.current.mutate("opt-a");
      });

      await act(async () => {
        vi.advanceTimersByTime(1200);
      });

      await waitFor(() => {
        expect(useWritingStore.getState().isGenerating).toBe(false);
      });
    });
  });

  describe("useSubmitCustomMutation", () => {
    it("returns a mutation hook", () => {
      const { result } = renderHook(() => useSubmitCustomMutation(), {
        wrapper: createWrapper(),
      });

      expect(result.current).toBeDefined();
      expect(typeof result.current.mutate).toBe("function");
    });

    it("mutation resolves with custom input after mock delay", async () => {
      const { result } = renderHook(() => useSubmitCustomMutation(), {
        wrapper: createWrapper(),
      });

      let data: unknown;
      act(() => {
        result.current.mutate("用户自定义内容", {
          onSuccess: (d) => { data = d; },
        });
      });

      await act(async () => {
        vi.advanceTimersByTime(1200);
      });

      await waitFor(() => {
        expect(data).toEqual({ success: true, input: "用户自定义内容" });
      });
    });

    it("resets isGenerating on success", async () => {
      useWritingStore.setState({ isGenerating: true });

      const { result } = renderHook(() => useSubmitCustomMutation(), {
        wrapper: createWrapper(),
      });

      act(() => {
        result.current.mutate("test");
      });

      await act(async () => {
        vi.advanceTimersByTime(1200);
      });

      await waitFor(() => {
        expect(useWritingStore.getState().isGenerating).toBe(false);
      });
    });
  });

  describe("useGenerateOptionsMutation", () => {
    it("returns a mutation hook", () => {
      const { result } = renderHook(() => useGenerateOptionsMutation(), {
        wrapper: createWrapper(),
      });

      expect(result.current).toBeDefined();
      expect(typeof result.current.mutate).toBe("function");
    });

    it("mutation resolves after mock delay", async () => {
      const { result } = renderHook(() => useGenerateOptionsMutation(), {
        wrapper: createWrapper(),
      });

      let data: unknown;
      act(() => {
        result.current.mutate(undefined, {
          onSuccess: (d) => { data = d; },
        });
      });

      await act(async () => {
        vi.advanceTimersByTime(1200);
      });

      await waitFor(() => {
        expect(data).toEqual({ success: true });
      });
    });

    it("resets isGenerating on success", async () => {
      useWritingStore.setState({ isGenerating: true });

      const { result } = renderHook(() => useGenerateOptionsMutation(), {
        wrapper: createWrapper(),
      });

      act(() => {
        result.current.mutate();
      });

      await act(async () => {
        vi.advanceTimersByTime(1200);
      });

      await waitFor(() => {
        expect(useWritingStore.getState().isGenerating).toBe(false);
      });
    });

    it("resets isGenerating on error", async () => {
      useWritingStore.setState({ isGenerating: true });

      // Override fetch to fail for this test
      globalThis.fetch = vi.fn().mockRejectedValue(new Error("Network error"));

      const { result } = renderHook(() => useGenerateOptionsMutation(), {
        wrapper: createWrapper(),
      });

      act(() => {
        result.current.mutate();
      });

      await waitFor(() => {
        expect(useWritingStore.getState().isGenerating).toBe(false);
      });
    });
  });
});
