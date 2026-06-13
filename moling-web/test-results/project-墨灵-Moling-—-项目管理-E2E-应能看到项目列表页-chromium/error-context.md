# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: project.spec.ts >> 墨灵 (Moling) — 项目管理 E2E >> 应能看到项目列表页
- Location: e2e\project.spec.ts:20:7

# Error details

```
Error: locator.fill: Page crashed
Call log:
  - waiting for getByLabel(/邮箱/i)

```

# Test source

```ts
  1  | import { test, expect } from '@playwright/test';
  2  | 
  3  | test.describe('墨灵 (Moling) — 项目管理 E2E', () => {
  4  |   test.beforeEach(async ({ page }) => {
  5  |     // 每次测试前先注册并登录
  6  |     const email = `e2e_${Date.now()}@moling.com`;
  7  |     const password = 'Password123!';
  8  | 
  9  |     await page.goto('/auth');
  10 |     // 点击注册标签
  11 |     await page.getByRole('button', { name: /注册/i }).first().click();
> 12 |     await page.getByLabel(/邮箱/i).fill(email);
     |                                  ^ Error: locator.fill: Page crashed
  13 |     await page.getByLabel(/用户名/i).fill('E2E测试用户');
  14 |     await page.getByLabel(/密码/i).fill(password);
  15 |     await page.getByLabel(/确认密码/i).fill(password);
  16 |     await page.getByRole('button', { name: /注册/i }).click();
  17 |     await page.waitForURL(/.*\/projects.*|.*\/workspace.*/);
  18 |   });
  19 | 
  20 |   test('应能看到项目列表页', async ({ page }) => {
  21 |     await expect(page.getByRole('heading', { name: /我的项目|My Projects/i })).toBeVisible();
  22 |   });
  23 | 
  24 |   test('创建新项目应成功', async ({ page }) => {
  25 |     await page.getByRole('link', { name: /新建项目|New Project/i }).first().click();
  26 |     await expect(page).toHaveURL(/.*\/projects\/new.*/);
  27 | 
  28 |     // 步骤 1：填写项目基本信息
  29 |     await page.getByLabel(/书名|Title/i).fill('E2E测试项目');
  30 |     await page.getByLabel(/作者|Author/i).fill('E2E作者');
  31 |     await page.getByLabel(/类型|Genre/i).selectOption({ label: /玄幻|Fantasy/i });
  32 |     await page.getByRole('button', { name: /下一步|Next/i }).click();
  33 | 
  34 |     // 步骤 2：选择创作模式（跳过或选择 from_scratch）
  35 |     await page.getByRole('button', { name: /从零开始|From Scratch|下一步|Next/i }).click();
  36 | 
  37 |     // 应跳转到工作台
  38 |     await expect(page).toHaveURL(/.*\/workspace.*/);
  39 |     await expect(page.getByText('E2E测试项目')).toBeVisible();
  40 |   });
  41 | 
  42 |   test('项目列表应显示已创建的项目', async ({ page }) => {
  43 |     // 先创建一个项目
  44 |     await page.getByRole('link', { name: /新建项目|New Project/i }).first().click();
  45 |     await page.getByLabel(/书名|Title/i).fill('列表测试项目');
  46 |     await page.getByLabel(/作者|Author/i).fill('作者');
  47 |     await page.getByLabel(/类型|Genre/i).selectOption({ label: /玄幻|Fantasy/i });
  48 |     await page.getByRole('button', { name: /下一步|Next/i }).click();
  49 |     await page.getByRole('button', { name: /从零开始|From Scratch|下一步|Next/i }).click();
  50 |     await page.waitForURL(/.*\/workspace.*/);
  51 | 
  52 |     // 返回项目列表
  53 |     await page.getByRole('link', { name: /我的项目|Projects/i }).first().click();
  54 |     await expect(page.getByText('列表测试项目')).toBeVisible();
  55 |   });
  56 | 
  57 |   test('删除项目应成功', async ({ page }) => {
  58 |     // 先创建一个项目
  59 |     await page.getByRole('link', { name: /新建项目|New Project/i }).first().click();
  60 |     await page.getByLabel(/书名|Title/i).fill('待删除项目');
  61 |     await page.getByLabel(/作者|Author/i).fill('作者');
  62 |     await page.getByLabel(/类型|Genre/i).selectOption({ label: /玄幻|Fantasy/i });
  63 |     await page.getByRole('button', { name: /下一步|Next/i }).click();
  64 |     await page.getByRole('button', { name: /从零开始|From Scratch|下一步|Next/i }).click();
  65 |     await page.waitForURL(/.*\/workspace.*/);
  66 | 
  67 |     // 返回项目列表
  68 |     await page.getByRole('link', { name: /我的项目|Projects/i }).first().click();
  69 | 
  70 |     // 点击删除按钮（假设有）
  71 |     await page.getByRole('button', { name: /删除|Delete/i }).first().click();
  72 |     await page.getByRole('button', { name: /确认|Confirm/i }).click();
  73 | 
  74 |     // 项目应消失
  75 |     await expect(page.getByText('待删除项目')).toBeHidden();
  76 |   });
  77 | });
  78 | 
```