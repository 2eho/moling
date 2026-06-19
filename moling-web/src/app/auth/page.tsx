"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Sparkles, Mail, Lock, User, ArrowLeft } from "lucide-react";

export default function AuthPage() {
  const router = useRouter();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [username, setUsername] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);

    // Simulate auth for now
    setTimeout(() => {
      setLoading(false);
      router.push("/projects");
    }, 800);
  };

  return (
    <div
      className="min-h-screen flex flex-col items-center justify-center px-4"
      style={{ background: "var(--th-bg)", color: "var(--th-text)" }}
    >
      {/* Back link */}
      <Link
        href="/"
        className="flex items-center gap-1.5 text-xs mb-8 transition-colors"
        style={{ color: "var(--th-text-3)" }}
      >
        <ArrowLeft size={14} />
        返回首页
      </Link>

      {/* Card */}
      <div className="glass-panel w-full max-w-sm p-8">
        {/* Logo */}
        <div className="flex items-center justify-center gap-2 mb-6">
          <div
            className="w-8 h-8 rounded-lg flex items-center justify-center"
            style={{
              background: "linear-gradient(135deg, var(--th-logo-from), var(--th-logo-to))",
              boxShadow: "0 2px 12px var(--th-accent-glow)",
            }}
          >
            <Sparkles size={16} className="text-white" />
          </div>
          <span className="text-lg font-bold">墨灵</span>
        </div>

        {/* Tabs */}
        <div className="flex mb-6 rounded-xl p-0.5" style={{ background: "var(--th-hover)" }}>
          {(["login", "register"] as const).map((m) => (
            <button
              key={m}
              onClick={() => { setMode(m); setError(""); }}
              className="flex-1 py-2 rounded-lg text-sm font-medium transition-all duration-200"
              style={{
                background: mode === m ? "var(--th-card)" : "transparent",
                color: mode === m ? "var(--th-text)" : "var(--th-text-3)",
              }}
            >
              {m === "login" ? "登录" : "注册"}
            </button>
          ))}
        </div>

        <form onSubmit={handleSubmit} className="flex flex-col gap-3.5">
          {mode === "register" && (
            <div className="relative">
              <User
                size={15}
                className="absolute left-3 top-1/2 -translate-y-1/2"
                style={{ color: "var(--th-text-3)" }}
              />
              <input
                type="text"
                placeholder="用户名"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                required={mode === "register"}
                className="w-full pl-10 pr-4 py-2.5 rounded-xl text-sm outline-none transition-all duration-200"
                style={{
                  background: "var(--th-input)",
                  border: "1px solid var(--th-border-subtle)",
                  color: "var(--th-text)",
                }}
              />
            </div>
          )}

          <div className="relative">
            <Mail
              size={15}
              className="absolute left-3 top-1/2 -translate-y-1/2"
              style={{ color: "var(--th-text-3)" }}
            />
            <input
              type="email"
              placeholder="邮箱"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              className="w-full pl-10 pr-4 py-2.5 rounded-xl text-sm outline-none transition-all duration-200"
              style={{
                background: "var(--th-input)",
                border: "1px solid var(--th-border-subtle)",
                color: "var(--th-text)",
              }}
            />
          </div>

          <div className="relative">
            <Lock
              size={15}
              className="absolute left-3 top-1/2 -translate-y-1/2"
              style={{ color: "var(--th-text-3)" }}
            />
            <input
              type="password"
              placeholder="密码"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              className="w-full pl-10 pr-4 py-2.5 rounded-xl text-sm outline-none transition-all duration-200"
              style={{
                background: "var(--th-input)",
                border: "1px solid var(--th-border-subtle)",
                color: "var(--th-text)",
              }}
            />
          </div>

          {error && (
            <p className="text-xs" style={{ color: "var(--th-danger)" }}>
              {error}
            </p>
          )}

          <button
            type="submit"
            disabled={loading}
            className="w-full py-2.5 rounded-xl text-sm font-semibold transition-all duration-200 disabled:opacity-50 mt-1"
            style={{
              background: "linear-gradient(135deg, var(--th-logo-from), var(--th-logo-to))",
              color: "#fff",
            }}
          >
            {loading ? "处理中..." : mode === "login" ? "登录" : "注册"}
          </button>
        </form>
      </div>
    </div>
  );
}
