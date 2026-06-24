import { ArrowLeft, Loader2, Lock, Mail, Sparkles, User } from "lucide-react";
import { useEffect, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { ApiError, apiPost } from "@/lib/http/client";

const SAVED_CREDS_KEY = "moling_saved_creds";

interface SavedCreds {
  email: string;
  password: string;
}

function loadSavedCreds(): SavedCreds | null {
  try {
    const raw = localStorage.getItem(SAVED_CREDS_KEY);
    if (!raw) return null;
    return JSON.parse(raw) as SavedCreds;
  } catch {
    return null;
  }
}

function saveCreds(creds: SavedCreds) {
  localStorage.setItem(SAVED_CREDS_KEY, JSON.stringify(creds));
}

function clearSavedCreds() {
  localStorage.removeItem(SAVED_CREDS_KEY);
}

/** Extract a human-readable message from an ApiError's data payload. */
function apiErrorMessage(err: ApiError): string {
  if (err.data !== null && typeof err.data === "object" && "message" in err.data) {
    return String(err.data.message);
  }
  return err.message;
}

export function AuthPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [mode, setMode] = useState<"login" | "register">(
    searchParams.get("mode") === "register" ? "register" : "login",
  );
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [nickname, setNickname] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [remember, setRemember] = useState(false);

  // Restore saved credentials on mount (login mode only)
  useEffect(() => {
    const currentMode = searchParams.get("mode") === "register" ? "register" : "login";
    if (currentMode === "login") {
      const saved = loadSavedCreds();
      if (saved) {
        setEmail(saved.email);
        setPassword(saved.password);
        setRemember(true);
      }
    }
  }, [searchParams]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      const endpoint = mode === "login" ? "/auth/login" : "/auth/register";
      const body = mode === "login" ? { email, password } : { email, password, nickname };

      const res = await apiPost<{ user?: { id: string; email: string } }>(endpoint, body);
      if (!res.user) throw new Error("登录响应缺少用户信息");

      // Persist or clear saved credentials
      if (mode === "login" && remember) {
        saveCreds({ email, password });
      } else {
        clearSavedCreds();
      }

      navigate("/projects");
    } catch (err: unknown) {
      if (err instanceof ApiError) {
        setError(apiErrorMessage(err));
      } else if (err instanceof Error) {
        setError(err.message);
      } else {
        setError("网络请求失败，请确认后端已启动");
      }
    } finally {
      setLoading(false);
    }
  };

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
              onClick={() => {
                setMode(m);
                setError("");
              }}
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
              <User
                size={15}
                className="absolute left-3.5 top-1/2 -translate-y-1/2 text-th-text-3"
              />
              <input
                type="text"
                placeholder="昵称"
                value={nickname}
                onChange={(e) => setNickname(e.target.value)}
                required={mode === "register"}
                minLength={2}
                className="w-full pl-10 pr-4 py-3 rounded-xl text-sm bg-th-input border border-th-border-subtle text-th-text placeholder:text-th-text-4 outline-none transition-all duration-200 focus:border-th-accent/50 focus:ring-2 focus:ring-th-accent-dim"
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
              className="w-full pl-10 pr-4 py-3 rounded-xl text-sm bg-th-input border border-th-border-subtle text-th-text placeholder:text-th-text-4 outline-none transition-all duration-200 focus:border-th-accent/50 focus:ring-2 focus:ring-th-accent-dim"
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
              className="w-full pl-10 pr-4 py-3 rounded-xl text-sm bg-th-input border border-th-border-subtle text-th-text placeholder:text-th-text-4 outline-none transition-all duration-200 focus:border-th-accent/50 focus:ring-2 focus:ring-th-accent-dim"
            />
          </div>

          {mode === "login" && (
            <label className="flex items-center gap-2 cursor-pointer select-none">
              <input
                type="checkbox"
                checked={remember}
                onChange={(e) => setRemember(e.target.checked)}
                className="w-4 h-4 rounded border-th-border-subtle accent-th-accent bg-th-input cursor-pointer"
              />
              <span className="text-xs text-th-text-3">记住账号密码</span>
            </label>
          )}

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
