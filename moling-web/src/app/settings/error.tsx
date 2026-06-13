"use client";

export default function SettingsError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <div style={{
      display: "flex",
      flexDirection: "column",
      alignItems: "center",
      justifyContent: "center",
      minHeight: "60vh",
      gap: "16px",
      color: "var(--color-text-secondary)",
    }}>
      <span style={{ fontSize: "48px" }}>⚠️</span>
      <h2 style={{ margin: 0, color: "var(--color-text-primary)" }}>加载出错</h2>
      <p style={{ margin: 0 }}>{error.message || "页面加载失败，请稍后重试"}</p>
      <button
        onClick={reset}
        style={{
          padding: "8px 24px",
          background: "var(--color-brand-primary)",
          color: "#fff",
          border: "none",
          borderRadius: "8px",
          cursor: "pointer",
          fontSize: "14px",
        }}
      >
        重新加载
      </button>
    </div>
  );
}
