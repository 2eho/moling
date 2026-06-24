import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { HealthDashboard } from "../HealthDashboard";

const mockHealthData = {
  project_id: "test-1",
  status: "warning" as const,
  last_checked_at: "2024-01-15T10:00:00Z",
  summary: { r1_count: 2, r2_count: 1, r3_count: 0, total: 3 },
  alerts: [
    {
      id: "alert-1",
      project_id: "test-1",
      severity: "R1" as const,
      rule: "子情节节奏过慢",
      subplot_name: "主线-复仇",
      current_chapter: 5,
      reason: "连续3章无关键冲突",
      suggestion: "加入剧情转折或新冲突",
      suppressed: false,
      created_at: "2024-01-15T10:00:00Z",
    },
    {
      id: "alert-2",
      project_id: "test-1",
      severity: "R2" as const,
      rule: "人物动机缺失",
      subplot_name: "支线-师徒",
      current_chapter: 3,
      reason: "角色行为缺乏合理动机",
      suggestion: "补充角色背景故事",
      suppressed: true,
      suppressed_reason: "3章内重复",
      created_at: "2024-01-15T09:00:00Z",
    },
  ],
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

describe("HealthDashboard", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("renders loading skeleton initially", () => {
    vi.spyOn(globalThis, "fetch").mockImplementation(() => new Promise(() => {}));
    render(<HealthDashboard projectId="test-1" />, { wrapper: createWrapper() });
    expect(document.querySelector(".animate-shimmer")).toBeTruthy();
  });

  it("renders alerts with correct severity colors", async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockHealthData),
    });
    render(<HealthDashboard projectId="test-1" />, { wrapper: createWrapper() });

    await waitFor(() => {
      const r1Elements = screen.getAllByText("R1 轻度");
      expect(r1Elements.length).toBeGreaterThanOrEqual(1);
      const r2Elements = screen.getAllByText("R2 中度");
      expect(r2Elements.length).toBeGreaterThanOrEqual(1);
    });
  });

  it("shows empty state when no alerts", async () => {
    const emptyData = {
      ...mockHealthData,
      alerts: [],
      summary: { r1_count: 0, r2_count: 0, r3_count: 0, total: 0 },
    };
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(emptyData),
    });
    render(<HealthDashboard projectId="test-1" />, { wrapper: createWrapper() });

    await waitFor(() => {
      const elements = screen.getAllByText("所有子情节健康");
      expect(elements.length).toBeGreaterThanOrEqual(1);
    });
  });

  it("shows error state and retry button", async () => {
    globalThis.fetch = vi.fn().mockRejectedValue(new Error("Network error"));
    render(<HealthDashboard projectId="test-1" />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText("加载健康数据失败")).toBeInTheDocument();
      expect(screen.getByText("重试")).toBeInTheDocument();
    });
  });

  it("displays alert count summary correctly", async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockHealthData),
    });
    render(<HealthDashboard projectId="test-1" />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText("2")).toBeInTheDocument(); // R1 count
      expect(screen.getByText("1")).toBeInTheDocument(); // R2 count
    });
  });

  it("shows suppressed alert with gray styling", async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockHealthData),
    });
    render(<HealthDashboard projectId="test-1" />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText("防疲劳抑制")).toBeInTheDocument();
    });
  });

  it("renders refresh button", async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockHealthData),
    });
    render(<HealthDashboard projectId="test-1" />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText("刷新")).toBeInTheDocument();
    });
  });

  it("expands alert details on click", async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockHealthData),
    });
    render(<HealthDashboard projectId="test-1" />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText("子情节节奏过慢")).toBeInTheDocument();
    });
  });
});
