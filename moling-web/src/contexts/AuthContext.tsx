"use client";

import {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
  useMemo,
  type ReactNode,
} from "react";
import type { User, ApiResponse } from "@/lib/types";
import { apiClient } from "@/lib/apiClient";
import {
  setTokens as storeTokens,
  setUser as storeUser,
  clearAuth,
  getUser as getStoredUser,
  isAuthenticated as checkAuth,
} from "@/lib/auth";

// ---- Types ----

interface LoginResponse {
  access_token: string;
  refresh_token: string;
  user: User;
}

type RegisterResponse = LoginResponse;

export interface AuthContextValue {
  /** Currently authenticated user, or null. */
  user: User | null;
  /** Whether the auth state is still being initialised from storage. */
  isLoading: boolean;
  /** Convenience derived flag. */
  isAuthenticated: boolean;
  /** Authenticate with email + password. */
  login: (email: string, password: string) => Promise<void>;
  /** Create a new account and auto-login. */
  register: (username: string, email: string, password: string) => Promise<void>;
  /** Clear all auth state and redirect. */
  logout: () => void;
  /** Send a password-reset email. */
  resetPassword: (email: string) => Promise<void>;
  /** Set a new password using a reset token. */
  setNewPassword: (token: string, password: string) => Promise<void>;
}

// ---- Context ----

const AuthContext = createContext<AuthContextValue | null>(null);

// ---- Provider ----

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUserState] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // Hydrate from localStorage on mount
  useEffect(() => {
    try {
      const storedUser = getStoredUser<User>();
      const authenticated = checkAuth();
      if (storedUser && authenticated) {
        setUserState(storedUser);
      }
    } catch {
      // Ignore — stay logged out
    } finally {
      setIsLoading(false);
    }
  }, []);

  // ---- Actions ----

  const login = useCallback(async (email: string, password: string) => {
    const res = await apiClient.post<ApiResponse<LoginResponse>>("/auth/login", {
      email,
      password,
    });
    const { access_token, refresh_token, user: userData } = res.data;
    storeTokens(access_token, refresh_token);
    storeUser(userData);
    setUserState(userData);
  }, []);

  const register = useCallback(
    async (username: string, email: string, password: string) => {
      // 后端 RegisterReq 接收的是 nickname（不是 username）
      const res = await apiClient.post<ApiResponse<RegisterResponse>>(
        "/auth/register",
        { nickname: username, email, password },
      );
      const { access_token, refresh_token, user: userData } = res.data;
      storeTokens(access_token, refresh_token);
      storeUser(userData);
      setUserState(userData);
    },
    [],
  );

  const logout = useCallback(() => {
    clearAuth();
    setUserState(null);
    window.location.href = "/auth";
  }, []);

  const resetPassword = useCallback(async (email: string) => {
    // 后端路径: POST /auth/password-reset-request
    await apiClient.post("/auth/password-reset-request", { email });
  }, []);

  const setNewPassword = useCallback(
    async (token: string, password: string) => {
      // 后端路径: POST /auth/password-reset
      await apiClient.post("/auth/password-reset", { token, new_password: password });
    },
    [],
  );

  // ---- Value ----

  const value = useMemo<AuthContextValue>(() => ({
    user,
    isLoading,
    isAuthenticated: !!user,
    login,
    register,
    logout,
    resetPassword,
    setNewPassword,
  }), [user, isLoading, login, register, logout, resetPassword, setNewPassword]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

// ---- Hook ----

/**
 * Access the current auth context.
 * Must be called within an `<AuthProvider>`.
 */
export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
