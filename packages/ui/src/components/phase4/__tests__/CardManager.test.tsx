import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { CardManager } from "../CardManager";

const mockCards = {
  items: [
    {
      id: "card-1",
      project_id: "test-1",
      content: "林风在绝境中领悟剑骨真谛，爆发出惊天剑气",
      type: "plot" as const,
      retired: false,
      freshness_period: "new" as const,
      created_at: "2024-01-15T10:00:00Z",
      updated_at: "2024-01-15T10:00:00Z",
    },
    {
      id: "card-2",
      project_id: "test-1",
      content: "老者的身份是上古剑宗传人",
      type: "character" as const,
      retired: true,
      retired_reason: "剧情线已完结",
      retired_chapter: 15,
      freshness_period: "stale" as const,
      created_at: "2024-01-10T10:00:00Z",
      updated_at: "2024-01-14T10:00:00Z",
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

describe("CardManager", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("renders cards from API data", async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockCards),
    });
    render(<CardManager projectId="test-1" />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText("新鲜")).toBeInTheDocument();
      expect(screen.getByText("陈旧")).toBeInTheDocument();
    });
  });

  it("shows retired status badge", async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockCards),
    });
    render(<CardManager projectId="test-1" />, { wrapper: createWrapper() });

    await waitFor(() => {
      const elements = screen.getAllByText("已退役");
      expect(elements.length).toBeGreaterThanOrEqual(1);
    });
  });

  it("renders filter tabs", async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockCards),
    });
    render(<CardManager projectId="test-1" />, { wrapper: createWrapper() });

    await waitFor(() => {
      const allElements = screen.getAllByText("全部");
      expect(allElements.length).toBeGreaterThanOrEqual(1);
      const activeElements = screen.getAllByText("活跃");
      expect(activeElements.length).toBeGreaterThanOrEqual(1);
      const retiredElements = screen.getAllByText("已退役");
      expect(retiredElements.length).toBeGreaterThanOrEqual(1);
    });
  });

  it("shows empty state when no cards", async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ items: [], total: 0, page: 1, page_size: 50 }),
    });
    render(<CardManager projectId="test-1" />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText("暂无卡牌")).toBeInTheDocument();
    });
  });

  it("shows error state with retry", async () => {
    globalThis.fetch = vi.fn().mockRejectedValue(new Error("API error"));
    render(<CardManager projectId="test-1" />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText("加载卡牌池失败")).toBeInTheDocument();
    });
  });

  it("displays freshness indicator", async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockCards),
    });
    render(<CardManager projectId="test-1" />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText("新鲜")).toBeInTheDocument();
    });
  });

  it("shows retired reason and chapter", async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockCards),
    });
    render(<CardManager projectId="test-1" />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText(/剧情线已完结/)).toBeInTheDocument();
    });
  });
});
