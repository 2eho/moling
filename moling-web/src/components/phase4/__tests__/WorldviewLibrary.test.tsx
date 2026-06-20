import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { WorldviewLibrary } from "../WorldviewLibrary";

const mockItems = {
  items: [
    {
      id: "wv-1",
      project_id: "test-1",
      name: "九州大陆",
      category: "geography" as const,
      description: "浩瀚无垠的大陆，分东西南北四方",
      details: "东方青龙域、西方白虎域、南方朱雀域、北方玄武域",
    },
  ],
  total: 1,
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
    return (
      <QueryClientProvider client={queryClient}>
        {children}
      </QueryClientProvider>
    );
  };
}

describe("WorldviewLibrary", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("renders worldview items with category labels", async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockItems),
    });
    render(<WorldviewLibrary projectId="test-1" />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText("九州大陆")).toBeInTheDocument();
      const geoElements = screen.getAllByText("地理");
      expect(geoElements.length).toBeGreaterThanOrEqual(1);
    });
  });

  it("shows empty state", async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ items: [], total: 0, page: 1, page_size: 50 }),
    });
    render(<WorldviewLibrary projectId="test-1" />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText("暂无世界观")).toBeInTheDocument();
    });
  });

  it("shows error state with retry", async () => {
    globalThis.fetch = vi.fn().mockRejectedValue(new Error("API error"));
    render(<WorldviewLibrary projectId="test-1" />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText("加载世界观库失败")).toBeInTheDocument();
    });
  });

  it("renders category filter buttons", async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockItems),
    });
    render(<WorldviewLibrary projectId="test-1" />, { wrapper: createWrapper() });

    await waitFor(() => {
      const allElements = screen.getAllByText("全部");
      expect(allElements.length).toBeGreaterThanOrEqual(1);
      const geoElements = screen.getAllByText("地理");
      expect(geoElements.length).toBeGreaterThanOrEqual(1);
      expect(screen.getByText("历史")).toBeInTheDocument();
    });
  });
});
