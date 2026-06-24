"use client";

import { AlertCircle, Download, Loader2, Upload } from "lucide-react";
import { useCallback, useState } from "react";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

type ImportFn = () => Promise<Record<string, unknown>>;
type ExportFn = (data: Record<string, unknown>) => Promise<void>;

// ---------------------------------------------------------------------------
// Tauri detection
// ---------------------------------------------------------------------------

function isTauri(): boolean {
  return typeof window !== "undefined" && "__TAURI_INTERNALS__" in window;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

interface ImportExportButtonsProps {
  /**
   * Typed import function injected from the host app's tauri-bridge.
   * Opens a native file dialog, reads the selected .moling file,
   * and returns parsed JSON.
   */
  importProject: ImportFn;
  /**
   * Typed export function injected from the host app's tauri-bridge.
   * Opens a native save dialog and writes the given data to a .moling file.
   */
  exportProject: ExportFn;
  /**
   * Called with the parsed project JSON when import succeeds.
   * The host app should forward this to the backend for validation.
   */
  onImport: (data: Record<string, unknown>) => Promise<void>;
  /**
   * Called when export is requested. The host app should fetch project
   * data from the backend and return it. Return null to cancel export.
   */
  onRequestExportData: () => Promise<Record<string, unknown> | null>;
  /** Label for the import button (default: "导入") */
  importLabel?: string;
  /** Label for the export button (default: "导出") */
  exportLabel?: string;
}

/**
 * Desktop-only import/export buttons for `.moling` project files.
 *
 * - **Import**: Opens native file dialog → reads .moling file → returns JSON
 *   → host calls backend API to import.
 * - **Export**: Host fetches project data from backend → opens native save dialog
 *   → writes .moling file.
 *
 * In browser / non-Tauri mode, this component renders nothing.
 */
export function ImportExportButtons({
  importProject,
  exportProject,
  onImport,
  onRequestExportData,
  importLabel = "导入",
  exportLabel = "导出",
}: ImportExportButtonsProps) {
  const [importing, setImporting] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  const clearMessages = useCallback(() => {
    setError(null);
    setSuccessMessage(null);
  }, []);

  const handleImport = useCallback(async () => {
    clearMessages();
    setImporting(true);
    try {
      const data = await importProject();
      await onImport(data);
      setSuccessMessage("项目导入成功");
      setTimeout(() => setSuccessMessage(null), 3000);
    } catch (err) {
      const msg = err instanceof Error ? err.message : "导入失败，请重试";
      setError(msg);
    } finally {
      setImporting(false);
    }
  }, [importProject, onImport, clearMessages]);

  const handleExport = useCallback(async () => {
    clearMessages();
    setExporting(true);
    try {
      const data = await onRequestExportData();
      if (!data) {
        // User cancelled or no data available
        setExporting(false);
        return;
      }
      await exportProject(data);
      setSuccessMessage("项目导出成功");
      setTimeout(() => setSuccessMessage(null), 3000);
    } catch (err) {
      const msg = err instanceof Error ? err.message : "导出失败，请重试";
      setError(msg);
    } finally {
      setExporting(false);
    }
  }, [exportProject, onRequestExportData, clearMessages]);

  // Hide entirely in browser mode
  if (!isTauri()) return null;

  const buttonBase =
    "inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[11px] font-medium transition-all duration-150 hover:opacity-85 active:scale-95 disabled:opacity-50 disabled:cursor-not-allowed";

  return (
    <div className="flex flex-col gap-1.5">
      <div className="flex items-center gap-2">
        <button
          type="button"
          onClick={handleImport}
          disabled={importing || exporting}
          className={buttonBase}
          style={{
            background: "var(--th-hover)",
            color: "var(--th-text-2)",
          }}
          aria-label={importLabel}
        >
          {importing ? <Loader2 size={12} className="animate-spin" /> : <Upload size={12} />}
          <span>{importing ? "导入中..." : importLabel}</span>
        </button>

        <button
          type="button"
          onClick={handleExport}
          disabled={importing || exporting}
          className={buttonBase}
          style={{
            background: "var(--th-hover)",
            color: "var(--th-text-2)",
          }}
          aria-label={exportLabel}
        >
          {exporting ? <Loader2 size={12} className="animate-spin" /> : <Download size={12} />}
          <span>{exporting ? "导出中..." : exportLabel}</span>
        </button>
      </div>

      {/* Feedback messages */}
      {error && (
        <div
          role="alert"
          className="flex items-center gap-1.5 text-[10px]"
          style={{ color: "var(--th-warning)" }}
        >
          <AlertCircle size={11} />
          <span>{error}</span>
        </div>
      )}
      {successMessage && (
        <div role="status" className="text-[10px]" style={{ color: "var(--th-accent)" }}>
          {successMessage}
        </div>
      )}
    </div>
  );
}
