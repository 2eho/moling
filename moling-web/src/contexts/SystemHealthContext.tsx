"use client";

import {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
  type ReactNode,
} from "react";
import type { SystemHealthStatus } from "@/lib/types";
import { systemHealthApi } from "@/lib/api";

// ---- Types ----

export interface SystemHealthContextValue {
  /** Current system health status, or null while loading. */
  health: SystemHealthStatus | null;
  /** Whether the health status is being fetched. */
  isLoading: boolean;
  /** Error message if the last fetch failed. */
  error: string | null;
  /** Manually trigger a health check refresh. */
  refresh: () => Promise<void>;
  /** Dismiss an R2-level warning (re-appears on next poll if still present). */
  dismissWarning: () => void;
  /** Whether the current R2 banner has been manually dismissed. */
  warningDismissed: boolean;
  /** Time in ms between health checks (default: 30000). */
  pollInterval: number;
}

// ---- Constants ----

const DEFAULT_POLL_INTERVAL = 30000; // 30 seconds

// ---- Context ----

const SystemHealthContext = createContext<SystemHealthContextValue | null>(null);

// ---- Provider ----

export function SystemHealthProvider({
  children,
  pollInterval = DEFAULT_POLL_INTERVAL,
}: {
  children: ReactNode;
  pollInterval?: number;
}) {
  const [health, setHealth] = useState<SystemHealthStatus | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [warningDismissed, setWarningDismissed] = useState(false);

  const fetchHealth = useCallback(async () => {
    try {
      setError(null);
      const res = await systemHealthApi.getStatus();
      setHealth(res.data);
    } catch (err) {
      const msg = err instanceof Error ? err.message : "无法获取系统健康状态";
      setError(msg);
    } finally {
      setIsLoading(false);
    }
  }, []);

  // Initial fetch
  useEffect(() => {
    fetchHealth();
  }, [fetchHealth]);

  // Polling
  useEffect(() => {
    const interval = setInterval(fetchHealth, pollInterval);
    return () => clearInterval(interval);
  }, [fetchHealth, pollInterval]);

  // Reset dismissed state when health level changes
  useEffect(() => {
    if (health?.level !== "R2") {
      setWarningDismissed(false);
    }
  }, [health?.level]);

  const refresh = useCallback(async () => {
    setIsLoading(true);
    await fetchHealth();
  }, [fetchHealth]);

  const dismissWarning = useCallback(() => {
    setWarningDismissed(true);
  }, []);

  const value: SystemHealthContextValue = {
    health,
    isLoading,
    error,
    refresh,
    dismissWarning,
    warningDismissed,
    pollInterval,
  };

  return (
    <SystemHealthContext.Provider value={value}>
      {children}
    </SystemHealthContext.Provider>
  );
}

// ---- Hook ----

/**
 * Access the current system health context.
 * Must be called within a `<SystemHealthProvider>`.
 */
export function useSystemHealth(): SystemHealthContextValue {
  const context = useContext(SystemHealthContext);
  if (!context) {
    throw new Error("useSystemHealth must be used within a SystemHealthProvider");
  }
  return context;
}
