export default function LandingLoading() {
  return (
    <div style={{
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      height: "100vh",
      background: "var(--color-bg, #0d0f1a)",
      color: "var(--color-text-tertiary, #6b7199)"
    }}>
      加载中...
    </div>
  );
}
