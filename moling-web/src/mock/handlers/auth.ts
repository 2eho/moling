/**
 * Mock Auth Handler — 开发模式下使用
 * 拦截 /auth/login 和 /auth/register 请求，返回 mock token
 */
export async function mockAuthLogin(body: { email: string; password: string }) {
  await new Promise((r) => setTimeout(r, 600));
  return {
    access_token: "mock_access_token_" + Date.now(),
    refresh_token: "mock_refresh_token_" + Date.now(),
    user: { id: "user-001", email: body.email, username: body.email.split("@")[0] },
  };
}

export async function mockAuthRegister(body: { email: string; password: string; username?: string }) {
  await new Promise((r) => setTimeout(r, 800));
  return {
    access_token: "mock_access_token_" + Date.now(),
    refresh_token: "mock_refresh_token_" + Date.now(),
    user: { id: "user-002", email: body.email, username: body.username || body.email.split("@")[0] },
  };
}
