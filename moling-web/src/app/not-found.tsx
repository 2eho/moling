import Link from "next/link";

export default function NotFound() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-[var(--th-bg)] p-8">
      <div className="text-center">
        <h1 className="mb-2 text-6xl font-bold text-[var(--th-accent)]">
          404
        </h1>
        <p className="mb-2 text-lg font-semibold text-[var(--th-text)]">
          页面不存在
        </p>
        <p className="mb-6 text-sm text-[var(--th-text-2)]">
          你访问的页面可能已被移除或不存在
        </p>
        <Link
          href="/projects"
          className="inline-flex items-center gap-2 rounded-lg bg-[var(--th-accent)] px-5 py-2.5 text-sm font-medium text-white transition-colors hover:bg-[var(--th-accent-hover)]"
        >
          返回项目列表
        </Link>
      </div>
    </div>
  );
}
