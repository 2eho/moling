export default function AdminLoading() {
  return (
    <div style={{
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      height: "100vh",
      background: "var(--color-admin-bg, #0a0c14)",
      color: "var(--color-text-tertiary, #6b7199)"
    }}>
      加载中...
    </div>
  );
}
