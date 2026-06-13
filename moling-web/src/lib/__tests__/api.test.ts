import { describe, it, expect, vi, beforeEach } from "vitest";

// Use vi.hoisted() to ensure mock fns are defined before hoisted vi.mock()
const { mockGet, mockPost, mockPut, mockPatch, mockDelete } = vi.hoisted(() => ({
  mockGet: vi.fn(),
  mockPost: vi.fn(),
  mockPut: vi.fn(),
  mockPatch: vi.fn(),
  mockDelete: vi.fn(),
}));

vi.mock("@/lib/apiClient", () => ({
  apiClient: {
    get: mockGet,
    post: mockPost,
    put: mockPut,
    patch: mockPatch,
    delete: mockDelete,
  },
}));

// Now import api modules after mock is set up
const { authApi } = await import("@/lib/api");
const { projectApi } = await import("@/lib/api");
const { chapterApi } = await import("@/lib/api");
const { cardApi } = await import("@/lib/api");
const { generationApi } = await import("@/lib/api");
const { vaultApi } = await import("@/lib/api");
const { healthApi } = await import("@/lib/api");

beforeEach(() => {
  vi.clearAllMocks();
});

// ===================== authApi =====================

describe("authApi", () => {
  it("login 调用 POST /auth/login", async () => {
    mockPost.mockResolvedValueOnce({ data: { access_token: "token" } });
    await authApi.login("test@test.com", "123456");
    expect(mockPost).toHaveBeenCalledWith("/auth/login", {
      email: "test@test.com",
      password: "123456",
    });
  });

  it("register 调用 POST /auth/register", async () => {
    mockPost.mockResolvedValueOnce({ data: {} });
    await authApi.register("user", "user@test.com", "pwd");
    expect(mockPost).toHaveBeenCalledWith("/auth/register", {
      username: "user",
      email: "user@test.com",
      password: "pwd",
    });
  });

  it("refreshToken 调用 POST /auth/refresh", async () => {
    mockPost.mockResolvedValueOnce({ data: {} });
    await authApi.refreshToken("rtoken");
    expect(mockPost).toHaveBeenCalledWith("/auth/refresh", {
      refresh_token: "rtoken",
    });
  });

  it("getMe 调用 GET /auth/me", async () => {
    mockGet.mockResolvedValueOnce({});
    await authApi.getMe();
    expect(mockGet).toHaveBeenCalledWith("/auth/me");
  });
});

// ===================== projectApi =====================

describe("projectApi", () => {
  it("list 调用 GET /projects（无搜索参数）", async () => {
    mockGet.mockResolvedValueOnce({ items: [] });
    await projectApi.list();
    expect(mockGet).toHaveBeenCalledWith("/projects");
  });

  it("list 带搜索词调用 GET /projects?q=xxx", async () => {
    mockGet.mockResolvedValueOnce({ items: [] });
    await projectApi.list("keyword");
    expect(mockGet).toHaveBeenCalledWith("/projects", { q: "keyword" });
  });

  it("getStats 调用 GET /projects/stats", async () => {
    mockGet.mockResolvedValueOnce({});
    await projectApi.getStats();
    expect(mockGet).toHaveBeenCalledWith("/projects/stats");
  });

  it("create 调用 POST /projects", async () => {
    mockPost.mockResolvedValueOnce({});
    await projectApi.create({ title: "New Project" });
    expect(mockPost).toHaveBeenCalledWith("/projects", {
      title: "New Project",
    });
  });

  it("getById 调用 GET /projects/{id}", async () => {
    mockGet.mockResolvedValueOnce({});
    await projectApi.getById("proj-123");
    expect(mockGet).toHaveBeenCalledWith("/projects/proj-123");
  });

  it("update 调用 PATCH /projects/{id}", async () => {
    mockPatch.mockResolvedValueOnce({});
    await projectApi.update("proj-456", { title: "Updated" });
    expect(mockPatch).toHaveBeenCalledWith("/projects/proj-456", {
      title: "Updated",
    });
  });

  it("delete 调用 DELETE /projects/{id}", async () => {
    mockDelete.mockResolvedValueOnce({ data: { deleted: true } });
    await projectApi.delete("proj-789");
    expect(mockDelete).toHaveBeenCalledWith("/projects/proj-789");
  });
});

// ===================== chapterApi =====================

describe("chapterApi", () => {
  it("getCurrent 调用 GET /projects/{projectId}/chapters/current", async () => {
    mockGet.mockResolvedValueOnce({ data: null });
    await chapterApi.getCurrent("pid-1");
    expect(mockGet).toHaveBeenCalledWith("/projects/pid-1/chapters/current");
  });

  it("list 调用 GET /projects/{projectId}/chapters?page=1&page_size=20", async () => {
    mockGet.mockResolvedValueOnce({ data: [] });
    await chapterApi.list("pid-2");
    expect(mockGet).toHaveBeenCalledWith("/projects/pid-2/chapters?page=1&page_size=20");
  });

  it("list 支持分页参数", async () => {
    mockGet.mockResolvedValueOnce({ data: [] });
    await chapterApi.list("pid-2", 2, 10);
    expect(mockGet).toHaveBeenCalledWith("/projects/pid-2/chapters?page=2&page_size=10");
  });

  it("create 抛出 Error 当缺少 project_id", async () => {
    await expect(
      chapterApi.create({ title: "No Project" }),
    ).rejects.toThrow("创建章节需要提供 project_id");
    expect(mockPost).not.toHaveBeenCalled();
  });

  it("create 调用 POST /projects/{projectId}/chapters", async () => {
    mockPost.mockResolvedValueOnce({ data: {} });
    await chapterApi.create({
      project_id: "pid-3",
      title: "Chapter 1",
    });
    expect(mockPost).toHaveBeenCalledWith("/projects/pid-3/chapters", {
      project_id: "pid-3",
      title: "Chapter 1",
    });
  });

  it("create(projectId, data) 便捷重载", async () => {
    mockPost.mockResolvedValueOnce({ data: {} });
    await chapterApi.create("pid-4", { title: "Ch 2" });
    expect(mockPost).toHaveBeenCalledWith("/projects/pid-4/chapters", {
      project_id: "pid-4",
      title: "Ch 2",
    });
  });

  it("deleteChapter 调用 DELETE /projects/{pid}/chapters/{id}", async () => {
    mockDelete.mockResolvedValueOnce({ data: {} });
    await chapterApi.deleteChapter("pid-1", "ch-del-1");
    expect(mockDelete).toHaveBeenCalledWith("/projects/pid-1/chapters/ch-del-1");
  });

  it("getById 调用 GET /projects/{pid}/chapters/{id}", async () => {
    mockGet.mockResolvedValueOnce({ data: null });
    await chapterApi.getById("pid-1", "ch-1");
    expect(mockGet).toHaveBeenCalledWith("/projects/pid-1/chapters/ch-1");
  });

  it("update 调用 PATCH /projects/{pid}/chapters/{id}", async () => {
    mockPatch.mockResolvedValueOnce({ data: {} });
    await chapterApi.update("pid-1", "ch-2", { title: "Updated Ch" });
    expect(mockPatch).toHaveBeenCalledWith("/projects/pid-1/chapters/ch-2", {
      title: "Updated Ch",
    });
  });
});

// ===================== cardApi =====================

describe("cardApi", () => {
  it("getPool 调用 GET /cards/pool 带 project_id 参数", async () => {
    mockGet.mockResolvedValueOnce({ data: [] });
    await cardApi.getPool("pid-10");
    expect(mockGet).toHaveBeenCalledWith("/cards/pool", {
      project_id: "pid-10",
    });
  });

  it("drawCards 调用 POST /cards/draw?project_id=&chapter_id=", async () => {
    mockPost.mockResolvedValueOnce({ data: {} });
    await cardApi.drawCards("pid-11", "ch-1", ["c1", "c2"], [1, 2], "normal");
    expect(mockPost).toHaveBeenCalledWith("/cards/draw?project_id=pid-11&chapter_id=ch-1", {
      keep_card_ids: ["c1", "c2"],
      weights: [1, 2],
      mode: "normal",
    });
  });

  it("redraw 调用 POST /cards/draw?project_id=&chapter_id=", async () => {
    mockPost.mockResolvedValueOnce({ data: {} });
    await cardApi.redraw("pid-12", "ch-2");
    expect(mockPost).toHaveBeenCalledWith("/cards/draw?project_id=pid-12&chapter_id=ch-2", {
      mode: "normal",
    });
  });

  it("getDrawHistory 调用 GET /cards/history", async () => {
    mockGet.mockResolvedValueOnce({ data: [] });
    await cardApi.getDrawHistory("pid-13");
    expect(mockGet).toHaveBeenCalledWith("/cards/history", { project_id: "pid-13" });
  });
});

// ===================== generationApi =====================

describe("generationApi", () => {
  it("generate 调用 POST /generation/trigger?project_id=&chapter_id=", async () => {
    mockPost.mockResolvedValueOnce({ data: {} });
    await generationApi.generate("pid-gen-1", "ch-gen-1", ["c1", "c2"]);
    expect(mockPost).toHaveBeenCalledWith(
      "/generation/trigger?project_id=pid-gen-1&chapter_id=ch-gen-1",
      { card_ids: ["c1", "c2"], weights: undefined, mode: undefined },
    );
  });

  it("generate 支持可选参数 weights 和 mode", async () => {
    mockPost.mockResolvedValueOnce({ data: {} });
    await generationApi.generate("pid-gen-1", "ch-gen-1", ["c1"], [1, 2], "double");
    expect(mockPost).toHaveBeenCalledWith(
      "/generation/trigger?project_id=pid-gen-1&chapter_id=ch-gen-1",
      { card_ids: ["c1"], weights: [1, 2], mode: "double" },
    );
  });

  it("getStatus 调用 GET /generation/task/{taskId}", async () => {
    mockGet.mockResolvedValueOnce({ data: {} });
    await generationApi.getStatus("task-1");
    expect(mockGet).toHaveBeenCalledWith("/generation/task/task-1");
  });

  it("cancel 调用 POST /generation/task/{taskId}/cancel", async () => {
    mockPost.mockResolvedValueOnce({ data: {} });
    await generationApi.cancel("task-2");
    expect(mockPost).toHaveBeenCalledWith("/generation/task/task-2/cancel");
  });

  it("confirm 调用 POST /projects/{projectId}/chapters/{chapterId}/confirm", async () => {
    mockPost.mockResolvedValueOnce({ data: {} });
    await generationApi.confirm("pid-conf-1", "ch-conf-1");
    expect(mockPost).toHaveBeenCalledWith("/projects/pid-conf-1/chapters/ch-conf-1/confirm");
  });

  it("revise 调用 POST /projects/{projectId}/chapters/{chapterId}/revise", async () => {
    mockPost.mockResolvedValueOnce({ data: {} });
    await generationApi.revise("pid-rev-1", "ch-rev-1");
    expect(mockPost).toHaveBeenCalledWith("/projects/pid-rev-1/chapters/ch-rev-1/revise");
  });

  it("getHistory 调用 GET /generation/history", async () => {
    mockGet.mockResolvedValueOnce({ data: {} });
    await generationApi.getHistory("pid-gen-2");
    expect(mockGet).toHaveBeenCalledWith("/generation/history?project_id=pid-gen-2&page=1&page_size=20");
  });

  it("getHistory 支持分页参数", async () => {
    mockGet.mockResolvedValueOnce({ data: {} });
    await generationApi.getHistory("pid-gen-2", 2, 10);
    expect(mockGet).toHaveBeenCalledWith("/generation/history?project_id=pid-gen-2&page=2&page_size=10");
  });
});

// ===================== vaultApi =====================

describe("vaultApi", () => {
  it("getCharacters 调用 GET /projects/{projectId}/vault/characters", async () => {
    mockGet.mockResolvedValueOnce({ data: [] });
    await vaultApi.getCharacters("pid-v-1");
    expect(mockGet).toHaveBeenCalledWith(
      "/projects/pid-v-1/vault/characters",
    );
  });

  it("getTimeline 调用 GET /projects/{projectId}/vault/timeline", async () => {
    mockGet.mockResolvedValueOnce({ data: [] });
    await vaultApi.getTimeline("pid-v-2");
    expect(mockGet).toHaveBeenCalledWith(
      "/projects/pid-v-2/vault/timeline",
    );
  });

  it("getPlotPromises 调用 GET /projects/{projectId}/vault/plot-promises", async () => {
    mockGet.mockResolvedValueOnce({ data: [] });
    await vaultApi.getPlotPromises("pid-v-3");
    expect(mockGet).toHaveBeenCalledWith(
      "/projects/pid-v-3/vault/plot-promises",
    );
  });

  it("getWorld 调用 GET /projects/{projectId}/vault/world", async () => {
    mockGet.mockResolvedValueOnce({ data: [] });
    await vaultApi.getWorld("pid-v-4");
    expect(mockGet).toHaveBeenCalledWith(
      "/projects/pid-v-4/vault/world",
    );
  });

  // ---- New vault methods ----

  it("updateCharacter 调用 PATCH /projects/{pid}/vault/characters/{id}", async () => {
    mockPatch.mockResolvedValueOnce({});
    await vaultApi.updateCharacter("pid-v-1", "char-1", { name: "新名字" });
    expect(mockPatch).toHaveBeenCalledWith("/projects/pid-v-1/vault/characters/char-1", {
      name: "新名字",
    });
  });

  it("deleteCharacter 调用 DELETE /projects/{pid}/vault/characters/{id}", async () => {
    mockDelete.mockResolvedValueOnce({});
    await vaultApi.deleteCharacter("pid-v-1", "char-1");
    expect(mockDelete).toHaveBeenCalledWith("/projects/pid-v-1/vault/characters/char-1");
  });

  it("updatePlotPromise 调用 PATCH /projects/{pid}/vault/plot-promises/{id}", async () => {
    mockPatch.mockResolvedValueOnce({});
    await vaultApi.updatePlotPromise("pid-v-1", "pp-1", { urgency: 5 });
    expect(mockPatch).toHaveBeenCalledWith("/projects/pid-v-1/vault/plot-promises/pp-1", {
      urgency: 5,
    });
  });

  it("deletePlotPromise 调用 DELETE /projects/{pid}/vault/plot-promises/{id}", async () => {
    mockDelete.mockResolvedValueOnce({});
    await vaultApi.deletePlotPromise("pid-v-1", "pp-1");
    expect(mockDelete).toHaveBeenCalledWith("/projects/pid-v-1/vault/plot-promises/pp-1");
  });

  it("getCharacterById 调用 GET /projects/{pid}/vault/characters/{id}", async () => {
    mockGet.mockResolvedValueOnce({});
    await vaultApi.getCharacterById("pid-v-1", "char-1");
    expect(mockGet).toHaveBeenCalledWith("/projects/pid-v-1/vault/characters/char-1");
  });

  it("createCharacter 调用 POST /projects/{pid}/vault/characters", async () => {
    mockPost.mockResolvedValueOnce({});
    await vaultApi.createCharacter("pid-v-1", { name: "新角色", role: "sidekick" });
    expect(mockPost).toHaveBeenCalledWith("/projects/pid-v-1/vault/characters", {
      name: "新角色",
      role: "sidekick",
    });
  });

  it("getTimelineEvents 调用 GET /projects/{pid}/vault/timeline", async () => {
    mockGet.mockResolvedValueOnce({});
    await vaultApi.getTimelineEvents("pid-v-1");
    expect(mockGet).toHaveBeenCalledWith("/projects/pid-v-1/vault/timeline");
  });

  it("getTimelineEventById 调用 GET /projects/{pid}/vault/timeline/{id}", async () => {
    mockGet.mockResolvedValueOnce({});
    await vaultApi.getTimelineEventById("pid-v-1", "tl-1");
    expect(mockGet).toHaveBeenCalledWith("/projects/pid-v-1/vault/timeline/tl-1");
  });

  it("createTimelineEvent 调用 POST /projects/{pid}/vault/timeline", async () => {
    mockPost.mockResolvedValueOnce({});
    await vaultApi.createTimelineEvent("pid-v-1", { chapter_number: 4, event: "入门", description: "..." });
    expect(mockPost).toHaveBeenCalledWith("/projects/pid-v-1/vault/timeline", {
      chapter_number: 4,
      event: "入门",
      description: "...",
    });
  });

  it("updateTimelineEvent 调用 PATCH /projects/{pid}/vault/timeline/{id}", async () => {
    mockPatch.mockResolvedValueOnce({});
    await vaultApi.updateTimelineEvent("pid-v-1", "tl-1", { impact: "重大" });
    expect(mockPatch).toHaveBeenCalledWith("/projects/pid-v-1/vault/timeline/tl-1", {
      impact: "重大",
    });
  });

  it("deleteTimelineEvent 调用 DELETE /projects/{pid}/vault/timeline/{id}", async () => {
    mockDelete.mockResolvedValueOnce({});
    await vaultApi.deleteTimelineEvent("pid-v-1", "tl-1");
    expect(mockDelete).toHaveBeenCalledWith("/projects/pid-v-1/vault/timeline/tl-1");
  });

  it("getPlotPromiseById 调用 GET /projects/{pid}/vault/plot-promises/{id}", async () => {
    mockGet.mockResolvedValueOnce({});
    await vaultApi.getPlotPromiseById("pid-v-1", "pp-1");
    expect(mockGet).toHaveBeenCalledWith("/projects/pid-v-1/vault/plot-promises/pp-1");
  });

  it("createPlotPromise 调用 POST /projects/{pid}/vault/plot-promises", async () => {
    mockPost.mockResolvedValueOnce({});
    await vaultApi.createPlotPromise("pid-v-1", { description: "新承诺", type: "mystery", urgency: 3 });
    expect(mockPost).toHaveBeenCalledWith("/projects/pid-v-1/vault/plot-promises", {
      description: "新承诺",
      type: "mystery",
      urgency: 3,
    });
  });

  it("getWorldEntryById 调用 GET /projects/{pid}/vault/world/{id}", async () => {
    mockGet.mockResolvedValueOnce({});
    await vaultApi.getWorldEntryById("pid-v-1", "wld-1");
    expect(mockGet).toHaveBeenCalledWith("/projects/pid-v-1/vault/world/wld-1");
  });

  it("createWorldEntry 调用 POST /projects/{pid}/vault/world", async () => {
    mockPost.mockResolvedValueOnce({});
    await vaultApi.createWorldEntry("pid-v-1", { term: "新概念", category: "地理", description: "..." });
    expect(mockPost).toHaveBeenCalledWith("/projects/pid-v-1/vault/world", {
      term: "新概念",
      category: "地理",
      description: "...",
    });
  });

  it("updateWorldEntry 调用 PATCH /projects/{pid}/vault/world/{id}", async () => {
    mockPatch.mockResolvedValueOnce({});
    await vaultApi.updateWorldEntry("pid-v-1", "wld-1", { description: "更新" });
    expect(mockPatch).toHaveBeenCalledWith("/projects/pid-v-1/vault/world/wld-1", {
      description: "更新",
    });
  });

  it("deleteWorldEntry 调用 DELETE /projects/{pid}/vault/world/{id}", async () => {
    mockDelete.mockResolvedValueOnce({});
    await vaultApi.deleteWorldEntry("pid-v-1", "wld-1");
    expect(mockDelete).toHaveBeenCalledWith("/projects/pid-v-1/vault/world/wld-1");
  });
});

// ===================== healthApi =====================

describe("healthApi", () => {
  it("getAlerts 调用 GET /projects/{projectId}/health/alerts", async () => {
    mockGet.mockResolvedValueOnce([]);
    await healthApi.getAlerts("pid-h-1");
    expect(mockGet).toHaveBeenCalledWith("/projects/pid-h-1/health/alerts");
  });

  it("refreshCheck 调用 POST /projects/{projectId}/health/refresh", async () => {
    mockPost.mockResolvedValueOnce([]);
    await healthApi.refreshCheck("pid-h-2");
    expect(mockPost).toHaveBeenCalledWith("/projects/pid-h-2/health/refresh");
  });
});
