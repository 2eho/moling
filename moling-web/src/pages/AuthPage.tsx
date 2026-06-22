import { useState } from "react";
import { useNavigate, useSearchParams, Link } from "react-router-dom";
import { Sparkles, Mail, Lock, User, ArrowLeft, Loader2 } from "lucide-react";
import { apiPost } from "@/lib/http/client";

export function AuthPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [mode, setMode] = useState<"login" | "register">(
    searchParams.get("mode") === "register" ? "register" : "login"
  );
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [nickname, setNickname] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      const endpoint = mode === "login" ? "/auth/login" : "/auth/register";
      const body = mode === "login"
        ? { email, password }
        : { email, password, nickname };

      const res = await apiPost<{ user?: { id: string; email: string } }>(endpoint, body);
      if (!res.user) throw new Error("登录响应缺少用户信息");
      navigate("/projects");
    } catch (err: any) {
      setError(err?.data?.message || err?.message || "网络请求失败，请确认后端已启动");
    } finally {
      setLoading(false);
    }
  };

  const inputClass = "w-full pl-10 pr-4 py-3 rounded-xl text-sm bg-th-input border border-th-border-subtle text-th-text placeholder:text-th-text-4 outline-none transition-all duration-200 focus:border-th-accent/50 focus:ring-2 focus:ring-th-accent-dim";

  return (
    <div className="min-h-screen flex flex-col items-center justify-center px-4 bg-th-bg text-th-text">
      <Link
        to="/"
        className="flex items-center gap-1.5 text-xs mb-10 text-th-text-3 hover:text-th-text-2 transition-colors"
      >
        <ArrowLeft size={14} />
        返回首页
      </Link>

      <div className="glass-panel w-full max-w-sm p-8">
        {/* Logo */}
        <div className="flex items-center justify-center gap-2.5 mb-8">
          <div className="w-9 h-9 rounded-xl flex items-center justify-center bg-gradient-to-br from-[var(--th-logo-from)] to-[var(--th-logo-to)] shadow-[0_2px_12px_var(--th-accent-glow)]">
            <Sparkles size={17} className="text-white" />
          </div>
          <span className="text-xl font-bold tracking-tight">墨灵</span>
        </div>

        {/* Mode Tabs */}
        <div className="flex mb-7 rounded-xl p-0.5 bg-th-hover">
          {(["login", "register"] as const).map((m) => (
            <button
              key={m}
              type="button"
              onClick={() => { setMode(m); setError(""); }}
              className={`flex-1 py-2.5 rounded-lg text-sm font-medium transition-all duration-200 ${
                mode === m
                  ? "bg-th-card text-th-text shadow-sm"
                  : "text-th-text-3 hover:text-th-text-2"
              }`}
            >
              {m === "login" ? "登录" : "注册"}
            </button>
          ))}
        </div>

        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          {mode === "register" && (
            <div className="relative">
              <User size={15} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-th-text-3" />
              <input
                type="text"
                placeholder="昵称"
                value={nickname}
                onChange={(e) => setNickname(e.target.value)}
                required={mode === "register"}
                minLength={2}
                className={inputClass}
              />
            </div>
          )}

          <div className="relative">
            <Mail size={15} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-th-text-3" />
            <input
              type="email"
              placeholder="邮箱"
              aria-label="用户名"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              className={inputClass}
            />
          </div>

          <div className="relative">
            <Lock size={15} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-th-text-3" />
            <input
              type="password"
              placeholder="密码"
              aria-label="密码"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              className={inputClass}
            />
          </div>

          {error && (
            <p className="text-xs text-th-danger bg-[var(--th-danger)]/8 px-3 py-2 rounded-lg">
              {error}
            </p>
          )}

          <button
            type="submit"
            disabled={loading}
            className="w-full py-3 rounded-xl text-sm font-semibold text-white bg-gradient-to-br from-[var(--th-logo-from)] to-[var(--th-logo-to)] hover:shadow-[0_4px_16px_var(--th-accent-glow)] disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-300 mt-1 flex items-center justify-center gap-2"
          >
            {loading && <Loader2 size={15} className="animate-spin" />}
            {loading ? "处理中..." : mode === "login" ? "登录" : "创建账号"}
          </button>
        </form>
      </div>
    </div>
  );
}
