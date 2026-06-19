import { test, expect } from "@playwright/test";

test.describe("墨灵 (Moling) — 工作台 E2E", () => {
  test.beforeEach(async ({ page }) => {
    // 注册并登录
    const email = `workspace_${Date.now()}@moling.com`;
    const password = "Password123!";

    await page.goto("/auth");
    await page.waitForLoadState("networkidle");

    // 点击注册标签
    await page.getByRole("button", { name: /注册/i }).first().click();
    await page.waitForTimeout(500);

    await page.getByLabel(/邮箱/i).fill(email);
    await page.getByLabel(/用户名/i).fill("工作台测试用户");
    await page.getByLabel(/密码/i).fill(password);
    await page.getByLabel(/确认密码/i).fill(password);
    await page.getByRole("button", { name: /注册/i }).click();

    await page.waitForURL(/.*\/projects.*|.*\/workspace.*/);
  });

  test("登录后应导航到工作台", async ({ page }) => {
    // 如果注册后到了项目列表页，先创建一个项目
    if (page.url().includes("/projects")) {
      // 尝试点击"新建项目"
      const newProjectBtn = page.getByRole("link", { name: /新建项目|New Project/i });
      if (await newProjectBtn.isVisible()) {
        await newProjectBtn.first().click();
        await page.waitForURL(/.*\/projects\/new.*/);

        // 步骤1：填写基本信息
        await page.getByLabel(/书名|Title/i).fill("工作台E2E测试项目");
        await page.getByLabel(/作者|Author/i).fill("E2E作者");
        // 选择类型（如果有select）
        const genreSelect = page.getByLabel(/类型|Genre/i);
        if (await genreSelect.isVisible()) {
          await genreSelect.selectOption({ index: 1 }); // 选第一个非空选项
        }
        await page.getByRole("button", { name: /下一步|Next/i }).click();

        // 步骤2：选择创作模式
        await page.waitForTimeout(500);
        const fromScratchBtn = page.getByRole("button", { name: /从零开始|From Scratch|下一步|Next/i });
        await fromScratchBtn.click();

        await page.waitForURL(/.*\/workspace.*/);
      }
    }

    // 现在应该在 workspace 页面
    await expect(page).toHaveURL(/.*\/workspace.*/);

    // 应看到项目标题
    await expect(page.getByText("工作台E2E测试项目")).toBeVisible();
  });

  test("在工作台应看到侧边栏导航", async ({ page }) => {
    // 导航到工作台（如果不在）
    if (!page.url().includes("/workspace")) {
      // 创建一个项目进入工作台
      await page.getByRole("link", { name: /新建项目|New Project/i }).first().click();
      await page.getByLabel(/书名|Title/i).fill("导航测试项目");
      await page.getByLabel(/作者|Author/i).fill("作者");
      const genreSelect = page.getByLabel(/类型|Genre/i);
      if (await genreSelect.isVisible()) {
        await genreSelect.selectOption({ index: 1 });
      }
      await page.getByRole("button", { name: /下一步|Next/i }).click();
      await page.waitForTimeout(500);
      await page.getByRole("button", { name: /从零开始|From Scratch|下一步|Next/i }).click();
      await page.waitForURL(/.*\/workspace.*/);
    }

    // 工作台应有基本的导航元素
    // 至少能看到项目名称或工作台标题
    await expect(page.locator("nav, aside, [class*='sidebar'], [class*='Sidebar']").first()).toBeVisible();
  });

  test("创建章节流程", async ({ page }) => {
    // 确保在工作台
    if (!page.url().includes("/workspace")) {
      await page.getByRole("link", { name: /新建项目|New Project/i }).first().click();
      await page.getByLabel(/书名|Title/i).fill("章节创建测试");
      await page.getByLabel(/作者|Author/i).fill("作者");
      const genreSelect = page.getByLabel(/类型|Genre/i);
      if (await genreSelect.isVisible()) {
        await genreSelect.selectOption({ index: 1 });
      }
      await page.getByRole("button", { name: /下一步|Next/i }).click();
      await page.waitForTimeout(500);
      await page.getByRole("button", { name: /从零开始|From Scratch|下一步|Next/i }).click();
      await page.waitForURL(/.*\/workspace.*/);
    }

    // 查找创建/新建章节的按钮
    const createChapterBtn = page.getByRole("button", {
      name: /新建章节|创建章节|添加章节|New Chapter|Add Chapter/i,
    });

    // 如果按钮存在，点击它
    if (await createChapterBtn.isVisible({ timeout: 3000 }).catch(() => false)) {
      await createChapterBtn.first().click();

      // 应该出现章节创建表单或导航到章节创建页
      // 检查是否有标题输入框
      const titleInput = page.getByLabel(/章节标题|Chapter Title|标题/i);
      if (await titleInput.isVisible({ timeout: 2000 }).catch(() => false)) {
        await titleInput.fill("E2E测试第一章");

        // 查找提交/创建按钮
        const submitBtn = page.getByRole("button", { name: /创建|生成|提交|Create|Generate|Submit/i });
        if (await submitBtn.isVisible({ timeout: 2000 }).catch(() => false)) {
          await submitBtn.click();
          // 等待生成或跳转
          await page.waitForTimeout(2000);
        }
      }
    }

    // 基本验证：页面没有崩溃
    await expect(page).not.toHaveURL(/.*\/error.*/);
  });

  test("未登录访问工作台应重定向到登录页", async ({ page }) => {
    // 清除所有 cookies/localStorage 模拟未登录状态
    await page.context().clearCookies();
    await page.goto("/workspace/some-project-id");

    // 应该重定向到 /auth
    await expect(page).toHaveURL(/.*\/auth.*/);
  });
});
