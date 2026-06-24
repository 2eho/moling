import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ForeshadowingLibrary } from "../ForeshadowingLibrary";

const mockItems = {
  items: [
    {
      id: "fs-1",
      project_id: "test-1",
      description: "神秘老者在月夜提及的远古预言",
      status: "active" as const,
      chapter_planted: 3,
    },
    {
      id: "fs-2",
      project_id: "test-1",
      description: "林风体内的剑骨封印",
      status: "redeemed" as const,
      chapter_planted: 1,
      chapter_redeemed: 10,
    },
  ],
  total: 2,
  page: 1,
  page_size: 50,
};

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  });
  return function Wrapper({ children }: { children: React.ReactNode }) {
    return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
  };
}

describe("ForeshadowingLibrary", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("renders foreshadowing items with status labels", async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockItems),
    });
    render(<ForeshadowingLibrary projectId="test-1" />, { wrapper: createWrapper() });

    await waitFor(() => {
      const activeElements = screen.getAllByText("活跃");
      expect(activeElements.length).toBeGreaterThanOrEqual(1);
      const redeemedElements = screen.getAllByText("已兑现");
      expect(redeemedElements.length).toBeGreaterThanOrEqual(1);
    });
  });

  it("shows empty state", async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ items: [], total: 0, page: 1, page_size: 50 }),
    });
    render(<ForeshadowingLibrary projectId="test-1" />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText("暂无情节承诺")).toBeInTheDocument();
    });
  });

  it("shows error state with retry", async () => {
    globalThis.fetch = vi.fn().mockRejectedValue(new Error("API error"));
    render(<ForeshadowingLibrary projectId="test-1" />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText("加载承诺库失败")).toBeInTheDocument();
    });
  });
});
