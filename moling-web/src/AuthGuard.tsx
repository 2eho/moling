import { type ReactNode, useEffect, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";

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
    (pattern) => pathname === pattern || pathname.startsWith(pattern + "/"),
  );
}

function getCookie(name: string): string | null {
  if (typeof document === "undefined") return null;
  const match = document.cookie.match(new RegExp(`(?:^|; )${name}=([^;]*)`));
  return match ? decodeURIComponent(match[1]) : null;
}

interface AuthGuardProps {
  children: ReactNode;
  fallback?: ReactNode;
}

export function AuthGuard({ children, fallback = null }: AuthGuardProps) {
  const navigate = useNavigate();
  const location = useLocation();
  const [isAuthorized, setIsAuthorized] = useState<boolean | null>(null);

  useEffect(() => {
    if (import.meta.env.VITE_SKIP_AUTH === "true" || import.meta.env.DEV) {
      setIsAuthorized(true);
      return;
    }

    if (!isProtectedRoute(location.pathname)) {
      setIsAuthorized(true);
      return;
    }

    const token = getCookie("access_token");
    if (token) {
      setIsAuthorized(true);
      return;
    }

    const params = new URLSearchParams();
    params.set("redirect", location.pathname);
    navigate(`/auth?${params.toString()}`, { replace: true });
  }, [location.pathname, navigate]);

  if (isAuthorized === null) {
    return <>{fallback}</>;
  }

  if (isAuthorized) {
    return <>{children}</>;
  }

  return null;
}
