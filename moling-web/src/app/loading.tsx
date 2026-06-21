export default function Loading() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-[var(--th-bg)]">
      <div className="h-8 w-8 animate-spin rounded-full border-2 border-[var(--th-border)] border-t-[var(--th-accent)]" />
    </div>
  );
}
