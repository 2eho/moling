# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: auth.spec.ts >> 墨灵 (Moling) — 认证流程 E2E >> 点击注册标签显示注册表单
- Location: e2e\auth.spec.ts:14:7

# Error details

```
Error: expect(locator).toBeVisible() failed

Locator: getByLabel(/邮箱/i)
Expected: visible
Timeout: 5000ms
Error: element(s) not found

Call log:
  - Expect "toBeVisible" with timeout 5000ms
  - waiting for getByLabel(/邮箱/i)

```

```yaml
- text: ✒
- heading "墨灵" [level=1]
- paragraph: AI 驱动的创意写作平台
- button "登录"
- button "注册"
- button "重置密码"
- text: 用户名 👤
- textbox "请输入用户名"
- text: 邮箱 ✉
- textbox "请输入邮箱地址"
- text: 密码 🔒
- textbox "请输入密码"
- text: 确认密码 🔒
- textbox "请再次输入密码"
- button "注册"
- alert
```

# Test source

```ts
  1  | import { test, expect } from '@playwright/test';
  2  | 
  3  | test.describe('墨灵 (Moling) — 认证流程 E2E', () => {
  4  |   test.beforeEach(async ({ page }) => {
  5  |     // 每次测试前跳转到首页
  6  |     await page.goto('/');
  7  |   });
  8  | 
  9  |   test('首页应显示登录按钮', async ({ page }) => {
  10 |     // 未登录状态应看到登录按钮
  11 |     await expect(page.getByRole('button', { name: /登录/i })).toBeVisible();
  12 |   });
  13 | 
  14 |   test('点击注册标签显示注册表单', async ({ page }) => {
  15 |     // 直接跳转到认证页
  16 |     await page.goto('/auth');
  17 |     // 等待注册标签可见
  18 |     await expect(page.getByRole('button', { name: /注册/i })).toBeVisible();
  19 |     // 点击注册标签
  20 |     await page.getByRole('button', { name: /注册/i }).first().click();
  21 |     // 等待表单渲染
  22 |     await page.waitForTimeout(1000);
  23 |     // 检查注册表单的邮箱输入框是否可见
> 24 |     await expect(page.getByLabel(/邮箱/i)).toBeVisible();
     |                                          ^ Error: expect(locator).toBeVisible() failed
  25 |   });
  26 | 
  27 |   test('注册新用户成功应跳转', async ({ page }) => {
  28 |     const email = `test_${Date.now()}@moling.com`;
  29 |     const password = 'Password123!';
  30 | 
  31 |     await page.goto('/auth');
  32 |     // 等待页面加载完成
  33 |     await page.waitForLoadState('networkidle');
  34 |     // 点击注册标签
  35 |     await page.getByRole('button', { name: /注册/i }).first().click();
  36 |     await page.getByLabel(/邮箱/i).fill(email);
  37 |     await page.getByLabel(/用户名/i).fill('E2E测试用户');
  38 |     await page.getByLabel(/密码/i).fill(password);
  39 |     await page.getByLabel(/确认密码/i).fill(password);
  40 |     await page.getByRole('button', { name: /注册/i }).click();
  41 | 
  42 |     // 注册成功应跳转到项目页或工作台
  43 |     await expect(page).toHaveURL(/.*\/projects.*|.*\/workspace.*/);
  44 |     await expect(page.getByText(/退出|登出|Logout/i)).toBeVisible();
  45 |   });
  46 | 
  47 |   test('使用注册账号登录成功', async ({ page }) => {
  48 |     // 先注册
  49 |     const email = `login_${Date.now()}@moling.com`;
  50 |     const password = 'Password123!';
  51 |     await page.goto('/auth');
  52 |     await page.getByLabel(/邮箱/i).fill(email);
  53 |     await page.getByLabel(/用户名/i).fill('登录测试用户');
  54 |     await page.getByLabel(/密码/i).fill(password);
  55 |     await page.getByLabel(/确认密码/i).fill(password);
  56 |     await page.getByRole('button', { name: /注册/i }).click();
  57 |     await page.waitForURL(/.*\/projects.*|.*\/workspace.*/);
  58 | 
  59 |     // 退出登录
  60 |     await page.getByText(/退出|登出|Logout/i).click();
  61 | 
  62 |     // 重新登录
  63 |     await page.goto('/auth');
  64 |     await page.getByLabel(/邮箱|Email/i).fill(email);
  65 |     await page.getByLabel(/密码|Password/i).fill(password);
  66 |     await page.getByRole('button', { name: /登录|Login/i }).click();
  67 | 
  68 |     await expect(page).toHaveURL(/.*\/projects.*|.*\/workspace.*/);
  69 |   });
  70 | 
  71 |   test('错误密码登录应显示错误提示', async ({ page }) => {
  72 |     await page.goto('/auth');
  73 |     await page.getByLabel(/邮箱|Email/i).fill('nonexistent@moling.com');
  74 |     await page.getByLabel(/密码|Password/i).fill('wrongpassword');
  75 |     await page.getByRole('button', { name: /登录|Login/i }).click();
  76 | 
  77 |     await expect(page.getByText(/错误|失败|error|invalid/i)).toBeVisible();
  78 |   });
  79 | 
  80 |   test('未登录访问 /workspace 应重定向到登录页', async ({ page }) => {
  81 |     await page.goto('/workspace/test-project-id');
  82 |     await expect(page).toHaveURL(/.*\/auth.*/);
  83 |   });
  84 | });
  85 | 
```