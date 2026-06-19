import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

const PROTECTED_PATTERNS = [
  "/projects",
  "/workspace",
  "/admin",
  "/settings",
  "/history",
  "/import",
  "/notifications",
  "/pricing",
  "/vaults",
  "/weave",
];

function isProtectedRoute(pathname: string): boolean {
  return PROTECTED_PATTERNS.some(
    (pattern) => pathname === pattern || pathname.startsWith(pattern + "/")
  );
}

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // 仅保护需要认证的路由
  if (!isProtectedRoute(pathname)) {
    return NextResponse.next();
  }

  // 开发模式跳过认证
  if (process.env.NEXT_PUBLIC_SKIP_AUTH === "true") {
    return NextResponse.next();
  }

  // 检查 token（从 cookie 或 header 中）
  const token =
    request.cookies.get("access_token")?.value ||
    request.headers.get("Authorization")?.replace("Bearer ", "");

  if (!token) {
    // BUGFIX: request.url 含 basePath，但 new URL("/auth", ...) 会丢掉 basePath
    // 必须显式拼接 "/moling/auth" 或用 request.nextUrl 重建
    const basePath = "/moling";
    const redirectUrl = new URL(basePath + "/auth", request.url);
    redirectUrl.searchParams.set("redirect", pathname);
    return NextResponse.redirect(redirectUrl);
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico|api/).*)"],
};
