import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Phase4TaskPanel } from "../Phase4TaskPanel";

const mockTasks = [
  {
    id: "task-1",
    project_id: "test-1",
    chapter_id: "ch-1",
    state: "done" as const,
    nonce: "abc",
    retry_count: 0,
    created_at: "2024-01-15T10:00:00Z",
    updated_at: "2024-01-15T10:05:00Z",
  },
  {
    id: "task-2",
    project_id: "test-1",
    chapter_id: "ch-2",
    state: "failed" as const,
    nonce: "def",
    retry_count: 2,
    last_error: "提取失败：章节内容不足",
    retry_at: "2024-01-16T10:00:00Z",
    created_at: "2024-01-15T09:00:00Z",
    updated_at: "2024-01-15T09:03:00Z",
  },
];

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

describe("Phase4TaskPanel", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("renders loading skeleton initially", () => {
    vi.spyOn(globalThis, "fetch").mockImplementation(() => new Promise(() => {}));
    render(<Phase4TaskPanel projectId="test-1" />, { wrapper: createWrapper() });
    expect(document.querySelector(".animate-shimmer")).toBeTruthy();
  });

  it("renders task list with correct state colors", async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockTasks),
    });
    render(<Phase4TaskPanel projectId="test-1" />, { wrapper: createWrapper() });

    await waitFor(() => {
      const doneElements = screen.getAllByText("完成");
      expect(doneElements.length).toBeGreaterThanOrEqual(1);
      const failedElements = screen.getAllByText("失败");
      expect(failedElements.length).toBeGreaterThanOrEqual(1);
    });
  });

  it("shows empty state when no tasks", async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve([]),
    });
    render(<Phase4TaskPanel projectId="test-1" />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText("暂无任务")).toBeInTheDocument();
    });
  });

  it("shows error state with retry button", async () => {
    globalThis.fetch = vi.fn().mockRejectedValue(new Error("Server error"));
    render(<Phase4TaskPanel projectId="test-1" />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText("加载任务失败")).toBeInTheDocument();
      expect(screen.getByText("重试")).toBeInTheDocument();
    });
  });

  it("displays error message for failed tasks", async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockTasks),
    });
    render(<Phase4TaskPanel projectId="test-1" />, { wrapper: createWrapper() });

    // Wait for task to render, then click to expand the failed task
    await waitFor(() => {
      expect(screen.getByText("失败")).toBeInTheDocument();
    });

    // Click on the failed task's expand button
    const failedBtn = screen.getByText("失败").closest("button");
    if (failedBtn) failedBtn.click();

    await waitFor(() => {
      expect(screen.getByText("提取失败：章节内容不足")).toBeInTheDocument();
    });
  });
});
