import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { TimelineLibrary } from "../TimelineLibrary";

const mockTimeline = {
  items: [
    {
      id: "tl-1",
      project_id: "test-1",
      chapter: 1,
      title: "宗门演武",
      date_label: "春季",
      description: "林风在宗门演武大会上初次展现实力",
      type: "event" as const,
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

describe("TimelineLibrary", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("renders timeline items from API", async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockTimeline),
    });
    render(<TimelineLibrary projectId="test-1" />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText("宗门演武")).toBeInTheDocument();
    });
  });

  it("shows empty state", async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ items: [], total: 0, page: 1, page_size: 50 }),
    });
    render(<TimelineLibrary projectId="test-1" />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText("暂无时间线")).toBeInTheDocument();
    });
  });

  it("shows error state", async () => {
    globalThis.fetch = vi.fn().mockRejectedValue(new Error("API error"));
    render(<TimelineLibrary projectId="test-1" />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText("加载时间线失败")).toBeInTheDocument();
    });
  });
});
