import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { CharacterLibrary } from "../CharacterLibrary";

const mockCharacters = {
  items: [
    {
      id: "char-1",
      project_id: "test-1",
      name: "林风",
      role: "protagonist" as const,
      description: "身怀绝世剑骨的少年",
      arc: "从废材到剑道宗师",
      chapter_introduced: 1,
      traits: ["坚韧", "执着", "正义"],
      relationships: ["师尊-剑无心"],
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

describe("CharacterLibrary", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("renders loading skeleton initially", () => {
    vi.spyOn(globalThis, "fetch").mockImplementation(() => new Promise(() => {}));
    render(<CharacterLibrary projectId="test-1" />, { wrapper: createWrapper() });
    expect(document.querySelector(".animate-shimmer")).toBeTruthy();
  });

  it("renders characters from API data", async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockCharacters),
    });
    render(<CharacterLibrary projectId="test-1" />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText("林风")).toBeInTheDocument();
      expect(screen.getByText("主角")).toBeInTheDocument();
    });
  });

  it("shows empty state when no characters", async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ items: [], total: 0, page: 1, page_size: 50 }),
    });
    render(<CharacterLibrary projectId="test-1" />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText("暂无角色")).toBeInTheDocument();
    });
  });

  it("shows error state with retry button", async () => {
    globalThis.fetch = vi.fn().mockRejectedValue(new Error("API error"));
    render(<CharacterLibrary projectId="test-1" />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText("加载角色库失败")).toBeInTheDocument();
      expect(screen.getByText("重试")).toBeInTheDocument();
    });
  });
});
