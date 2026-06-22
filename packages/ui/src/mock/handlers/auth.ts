/**
 * Mock Auth Handler — 开发模式下使用
 * 拦截 /auth/login 和 /auth/register 请求，返回 mock 响应。
 *
 * 生产环境中 token 通过 httpOnly Cookie 传输：
 * - 后端在响应中通过 Set-Cookie 设置 access_token 和 refresh_token
 * - 前端 JS 无法读取 token 值，所有请求通过 cookie 自动携带
 * - 本 mock 返回的 access_token/refresh_token 仅用于标记，
 *   mock 拦截器应模拟 Set-Cookie 行为（如写入 document.cookie 或内存模拟）
 */
export async function mockAuthLogin(body: { email: string; password: string }) {
  await new Promise((r) => setTimeout(r, 600));
  // 生产环境中，后端通过 Set-Cookie 设置以下 httpOnly Cookie：
  //   Set-Cookie: access_token=mock_access_token_...; HttpOnly; Secure; SameSite=Lax; Path=/; Max-Age=3600
  //   Set-Cookie: refresh_token=mock_refresh_token_...; HttpOnly; Secure; SameSite=Lax; Path=/auth; Max-Age=604800
  return {
    access_token: "mock_access_token_" + Date.now(),
    refresh_token: "mock_refresh_token_" + Date.now(),
    user: { id: "user-001", email: body.email, username: body.email.split("@")[0] },
  };
}

export async function mockAuthRegister(body: { email: string; password: string; username?: string }) {
  await new Promise((r) => setTimeout(r, 800));
  // 生产环境中，后端通过 Set-Cookie 设置 httpOnly Cookie（同 mockAuthLogin）
  return {
    access_token: "mock_access_token_" + Date.now(),
    refresh_token: "mock_refresh_token_" + Date.now(),
    user: { id: "user-002", email: body.email, username: body.username || body.email.split("@")[0] },
  };
}
