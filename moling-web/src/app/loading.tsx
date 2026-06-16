export default function RootLoading() {
  return (
    <div style={{
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      height: "100vh",
      background: "var(--color-bg, #0d0f1a)",
      color: "var(--color-text-tertiary, #6b7199)"
    }}>
      <div style={{ textAlign: "center" }}>
        <div style={{
          width: "40px",
          height: "40px",
          border: "3px solid var(--color-border, #2a2d45)",
          borderTop: "3px solid var(--color-brand-indigo, #6366f1)",
          borderRadius: "50%",
          animation: "spin 1s linear infinite",
          margin: "0 auto 16px"
        }} />
        <div>加载中...</div>
      </div>
    </div>
  );
}
