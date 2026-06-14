import { test, expect } from '@playwright/test';

test.describe('墨灵 (Moling) — 项目管理 E2E', () => {
  test.beforeEach(async ({ page }) => {
    // 每次测试前先注册并登录
    const email = `e2e_${Date.now()}@moling.com`;
    const password = 'Password123!';

    await page.goto('/auth');
    // 点击注册标签
    await page.getByRole('button', { name: /注册/i }).first().click();
    await page.getByLabel(/邮箱/i).fill(email);
    await page.getByLabel(/用户名/i).fill('E2E测试用户');
    await page.getByLabel(/密码/i).fill(password);
    await page.getByLabel(/确认密码/i).fill(password);
    await page.getByRole('button', { name: /注册/i }).click();
    await page.waitForURL(/.*\/projects.*|.*\/workspace.*/);
  });

  test('应能看到项目列表页', async ({ page }) => {
    await expect(page.getByRole('heading', { name: /我的项目|My Projects/i })).toBeVisible();
  });

  test('创建新项目应成功', async ({ page }) => {
    await page.getByRole('link', { name: /新建项目|New Project/i }).first().click();
    await expect(page).toHaveURL(/.*\/projects\/new.*/);

    // 步骤 1：填写项目基本信息
    await page.getByLabel(/书名|Title/i).fill('E2E测试项目');
    await page.getByLabel(/作者|Author/i).fill('E2E作者');
    await page.getByLabel(/类型|Genre/i).selectOption({ label: '玄幻' } as any);
    await page.getByRole('button', { name: /下一步|Next/i }).click();

    // 步骤 2：选择创作模式（跳过或选择 from_scratch）
    await page.getByRole('button', { name: /从零开始|From Scratch|下一步|Next/i }).click();

    // 应跳转到工作台
    await expect(page).toHaveURL(/.*\/workspace.*/);
    await expect(page.getByText('E2E测试项目')).toBeVisible();
  });

  test('项目列表应显示已创建的项目', async ({ page }) => {
    // 先创建一个项目
    await page.getByRole('link', { name: /新建项目|New Project/i }).first().click();
    await page.getByLabel(/书名|Title/i).fill('列表测试项目');
    await page.getByLabel(/作者|Author/i).fill('作者');
    await page.getByLabel(/类型|Genre/i).selectOption({ label: '玄幻' } as any);
    await page.getByRole('button', { name: /下一步|Next/i }).click();
    await page.getByRole('button', { name: /从零开始|From Scratch|下一步|Next/i }).click();
    await page.waitForURL(/.*\/workspace.*/);

    // 返回项目列表
    await page.getByRole('link', { name: /我的项目|Projects/i }).first().click();
    await expect(page.getByText('列表测试项目')).toBeVisible();
  });

  test('删除项目应成功', async ({ page }) => {
    // 先创建一个项目
    await page.getByRole('link', { name: /新建项目|New Project/i }).first().click();
    await page.getByLabel(/书名|Title/i).fill('待删除项目');
    await page.getByLabel(/作者|Author/i).fill('作者');
    await page.getByLabel(/类型|Genre/i).selectOption({ label: '玄幻' } as any);
    await page.getByRole('button', { name: /下一步|Next/i }).click();
    await page.getByRole('button', { name: /从零开始|From Scratch|下一步|Next/i }).click();
    await page.waitForURL(/.*\/workspace.*/);

    // 返回项目列表
    await page.getByRole('link', { name: /我的项目|Projects/i }).first().click();

    // 点击删除按钮（假设有）
    await page.getByRole('button', { name: /删除|Delete/i }).first().click();
    await page.getByRole('button', { name: /确认|Confirm/i }).click();

    // 项目应消失
    await expect(page.getByText('待删除项目')).toBeHidden();
  });
});
