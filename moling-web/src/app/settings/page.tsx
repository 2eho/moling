"use client";

import Link from "next/link";
import { ArrowLeft, User } from "lucide-react";

export default function SettingsPage() {
  return (
    <div
      className="min-h-screen flex flex-col"
      style={{ background: "var(--th-bg)", color: "var(--th-text)" }}
    >
      <header className="flex items-center gap-3 px-6 py-4">
        <Link href="/projects" style={{ color: "var(--th-text-3)" }}>
          <ArrowLeft size={20} />
        </Link>
        <span className="text-base font-bold">设置</span>
      </header>

      <main className="flex-1 max-w-lg mx-auto w-full px-6 py-8">
        <div className="glass-card p-5">
          <div className="flex items-center gap-3 mb-4">
            <div
              className="w-10 h-10 rounded-full flex items-center justify-center"
              style={{ background: "var(--th-accent-dim)" }}
            >
              <User size={20} style={{ color: "var(--th-accent-text)" }} />
            </div>
            <div>
              <p className="text-sm font-medium">用户</p>
              <p className="text-xs" style={{ color: "var(--th-text-3)" }}>
                admin@moling.dev
              </p>
            </div>
          </div>

          <div className="flex flex-col gap-1">
            {[
              { label: "修改密码", href: "#" },
              { label: "通知设置", href: "#" },
              { label: "LLM 配置", href: "#" },
              { label: "关于墨灵", href: "#" },
            ].map((item) => (
              <Link
                key={item.label}
                href={item.href}
                className="px-3 py-2.5 rounded-lg text-sm transition-colors"
                style={{ color: "var(--th-text-2)" }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.background = "var(--th-hover)";
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.background = "transparent";
                }}
              >
                {item.label}
              </Link>
            ))}
          </div>
        </div>
      </main>
    </div>
  );
}
