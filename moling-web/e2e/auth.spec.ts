import { test, expect } from '@playwright/test';

test.describe('墨灵 (Moling) — 认证流程 E2E', () => {
  test.beforeEach(async ({ page }) => {
    // 每次测试前跳转到首页
    await page.goto('/');
  });

  test('首页应显示登录按钮', async ({ page }) => {
    // 未登录状态应看到登录按钮
    await expect(page.getByRole('button', { name: /登录/i })).toBeVisible();
  });

  test('点击注册标签显示注册表单', async ({ page }) => {
    // 直接跳转到认证页
    await page.goto('/auth');
    // 等待注册标签可见
    await expect(page.getByRole('button', { name: /注册/i })).toBeVisible();
    // 点击注册标签
    await page.getByRole('button', { name: /注册/i }).first().click();
    // 等待表单渲染
    await page.waitForTimeout(1000);
    // 检查注册表单的邮箱输入框是否可见
    await expect(page.getByLabel(/邮箱/i)).toBeVisible();
  });

  test('注册新用户成功应跳转', async ({ page }) => {
    const email = `test_${Date.now()}@moling.com`;
    const password = 'Password123!';

    await page.goto('/auth');
    // 等待页面加载完成
    await page.waitForLoadState('networkidle');
    // 点击注册标签
    await page.getByRole('button', { name: /注册/i }).first().click();
    await page.getByLabel(/邮箱/i).fill(email);
    await page.getByLabel(/用户名/i).fill('E2E测试用户');
    await page.getByLabel(/密码/i).fill(password);
    await page.getByLabel(/确认密码/i).fill(password);
    await page.getByRole('button', { name: /注册/i }).click();

    // 注册成功应跳转到项目页或工作台
    await expect(page).toHaveURL(/.*\/projects.*|.*\/workspace.*/);
    await expect(page.getByText(/退出|登出|Logout/i)).toBeVisible();
  });

  test('使用注册账号登录成功', async ({ page }) => {
    // 先注册
    const email = `login_${Date.now()}@moling.com`;
    const password = 'Password123!';
    await page.goto('/auth');
    await page.getByLabel(/邮箱/i).fill(email);
    await page.getByLabel(/用户名/i).fill('登录测试用户');
    await page.getByLabel(/密码/i).fill(password);
    await page.getByLabel(/确认密码/i).fill(password);
    await page.getByRole('button', { name: /注册/i }).click();
    await page.waitForURL(/.*\/projects.*|.*\/workspace.*/);

    // 退出登录
    await page.getByText(/退出|登出|Logout/i).click();

    // 重新登录
    await page.goto('/auth');
    await page.getByLabel(/邮箱|Email/i).fill(email);
    await page.getByLabel(/密码|Password/i).fill(password);
    await page.getByRole('button', { name: /登录|Login/i }).click();

    await expect(page).toHaveURL(/.*\/projects.*|.*\/workspace.*/);
  });

  test('错误密码登录应显示错误提示', async ({ page }) => {
    await page.goto('/auth');
    await page.getByLabel(/邮箱|Email/i).fill('nonexistent@moling.com');
    await page.getByLabel(/密码|Password/i).fill('wrongpassword');
    await page.getByRole('button', { name: /登录|Login/i }).click();

    await expect(page.getByText(/错误|失败|error|invalid/i)).toBeVisible();
  });

  test('未登录访问 /workspace 应重定向到登录页', async ({ page }) => {
    await page.goto('/workspace/test-project-id');
    await expect(page).toHaveURL(/.*\/auth.*/);
  });
});
