"use client";

import { Download, ExternalLink, X } from "lucide-react";
import { useCallback, useEffect, useState } from "react";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface UpdateInfo {
  version: string;
  body: string | null;
  date: string | null;
}

// ---------------------------------------------------------------------------
// Tauri bridge (thin — only checks for updates, doesn't install)
// ---------------------------------------------------------------------------

type CheckUpdateFn = () => Promise<{
  available: boolean;
  version: string | null;
  body: string | null;
  date: string | null;
}>;

function isTauri(): boolean {
  return typeof window !== "undefined" && "__TAURI_INTERNALS__" in window;
}

async function checkForUpdates(checkFn: CheckUpdateFn): Promise<UpdateInfo | null> {
  if (!isTauri()) return null;
  try {
    const result = await checkFn();
    if (result.available && result.version) {
      return {
        version: result.version,
        body: result.body,
        date: result.date,
      };
    }
    return null;
  } catch {
    // Network error or updater not configured — silently ignore
    return null;
  }
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

interface UpdateNotificationProps {
  /** Typed check function injected from the host app's tauri-bridge. */
  checkUpdate: CheckUpdateFn;
}

/**
 * Desktop-only update notification banner.
 *
 * Checks for updates on mount and displays a subtle banner at the top of the
 * screen when a new version is available. The user can dismiss the banner or
 * click through to download the update.
 *
 * In browser / non-Tauri mode, this component renders nothing.
 */
export function UpdateNotification({ checkUpdate }: UpdateNotificationProps) {
  const [update, setUpdate] = useState<UpdateInfo | null>(null);
  const [dismissed, setDismissed] = useState(false);
  const [checking, setChecking] = useState(true);

  useEffect(() => {
    let cancelled = false;

    async function run() {
      const info = await checkForUpdates(checkUpdate);
      if (!cancelled && info) {
        setUpdate(info);
      }
      if (!cancelled) {
        setChecking(false);
      }
    }

    run();

    return () => {
      cancelled = true;
    };
  }, [checkUpdate]);

  const handleDismiss = useCallback(() => {
    setDismissed(true);
  }, []);

  // Nothing to show
  if (checking || !update || dismissed) return null;

  const bodyPreview =
    update.body && update.body.length > 120 ? update.body.slice(0, 120) + "…" : update.body;

  return (
    <div
      role="alert"
      aria-live="polite"
      className="fixed top-0 left-0 right-0 z-[100] flex items-center justify-between gap-3 px-5 py-2.5 text-xs animate-slide-down bg-th-accent-dim border-b border-th-accent text-th-accent-text"
    >
      <div className="flex items-center gap-3 min-w-0">
        <Download size={14} className="shrink-0 text-th-accent" />
        <span className="font-medium shrink-0">新版本 {update.version}</span>
        {bodyPreview && (
          <span className="truncate hidden sm:inline text-th-text-2">· {bodyPreview}</span>
        )}
      </div>

      <div className="flex items-center gap-2 shrink-0">
        <button
          type="button"
          onClick={() => {
            // Open release page — host app can override via updater JS API
            window.open("https://github.com/moling/desktop/releases/latest", "_blank");
          }}
          className="inline-flex items-center gap-1 px-3 py-1 rounded-md text-[11px] font-medium transition-all hover:opacity-85 active:scale-95 bg-th-accent text-white"
        >
          <ExternalLink size={11} />
          查看
        </button>
        <button
          type="button"
          onClick={handleDismiss}
          aria-label="关闭更新提示"
          className="p-1 rounded-md transition-all hover:opacity-70 text-th-text-3"
        >
          <X size={13} />
        </button>
      </div>
    </div>
  );
}
