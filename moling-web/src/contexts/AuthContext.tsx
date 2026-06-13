"use client";

import {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
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
      const res = await apiClient.post<ApiResponse<RegisterResponse>>(
        "/auth/register",
        { username, email, password },
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
    await apiClient.post("/auth/reset-password", { email });
  }, []);

  const setNewPassword = useCallback(
    async (token: string, password: string) => {
      await apiClient.post("/auth/set-password", { token, password });
    },
    [],
  );

  // ---- Value ----

  const value: AuthContextValue = {
    user,
    isLoading,
    isAuthenticated: !!user,
    login,
    register,
    logout,
    resetPassword,
    setNewPassword,
  };

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
