import Link from "next/link";
import { Sparkles, ArrowRight, PenTool, Brain, GitBranch, Users } from "lucide-react";

export default function LandingPage() {
  return (
    <div
      className="min-h-screen flex flex-col"
      style={{ background: "var(--th-bg)", color: "var(--th-text)" }}
    >
      {/* Nav */}
      <nav className="flex items-center justify-between px-6 py-4">
        <div className="flex items-center gap-2">
          <div
            className="w-8 h-8 rounded-lg flex items-center justify-center"
            style={{
              background: "linear-gradient(135deg, var(--th-logo-from), var(--th-logo-to))",
              boxShadow: "0 2px 12px var(--th-accent-glow)",
            }}
          >
            <Sparkles size={16} className="text-white" />
          </div>
          <span className="text-base font-bold">墨灵</span>
        </div>
        <div className="flex items-center gap-3">
          <Link
            href="/auth"
            className="px-4 py-2 rounded-xl text-sm font-medium transition-all duration-200"
            style={{ color: "var(--th-text-2)" }}
          >
            登录
          </Link>
          <Link
            href="/auth?mode=register"
            className="px-4 py-2 rounded-xl text-sm font-medium transition-all duration-200"
            style={{
              background: "var(--th-accent-dim)",
              color: "var(--th-accent-text)",
            }}
          >
            注册
          </Link>
        </div>
      </nav>

      {/* Hero */}
      <main className="flex-1 flex flex-col items-center justify-center px-6 text-center">
        <div
          className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full mb-8 text-xs font-medium"
          style={{
            background: "var(--th-accent-dim)",
            color: "var(--th-accent-text)",
            border: "1px solid var(--th-accent-dim)",
          }}
        >
          <Sparkles size={12} />
          Agent of Agents — 选择推进，灵感不中断
        </div>

        <h1 className="text-4xl md:text-5xl font-bold mb-4 tracking-tight leading-tight">
          AI 驱动的
          <br />
          <span style={{ color: "var(--th-accent-text)" }}>网文创作引擎</span>
        </h1>

        <p
          className="text-base md:text-lg max-w-lg mb-10 leading-relaxed"
          style={{ color: "var(--th-text-3)" }}
        >
          告别空白页面的恐惧。墨灵用 A/B/C 选项引导你的创作方向，
          让每个章节都有 AI Agent 团队为你保驾护航。
        </p>

        <Link
          href="/auth?mode=register"
          className="group flex items-center gap-2 px-8 py-3 rounded-2xl text-base font-semibold transition-all duration-300 hover:scale-105 active:scale-95"
          style={{
            background: "linear-gradient(135deg, var(--th-logo-from), var(--th-logo-to))",
            color: "#fff",
            boxShadow: "0 4px 24px var(--th-accent-glow)",
          }}
        >
          开始创作
          <ArrowRight size={18} className="group-hover:translate-x-1 transition-transform" />
        </Link>

        {/* Feature cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-16 max-w-3xl w-full">
          {[
            {
              icon: <Brain size={20} />,
              title: "Agent 协作",
              desc: "多 Agent 并行分析，从剧情、人物、对话多维度提供选择",
            },
            {
              icon: <GitBranch size={20} />,
              title: "A/B/C 选项",
              desc: "每次决策三个方向，点击即推进，灵感永不中断",
            },
            {
              icon: <Users size={20} />,
              title: "四库系统",
              desc: "角色库、情节承诺库、世界观库、伏笔钩子库自动追踪",
            },
          ].map((f) => (
            <div
              key={f.title}
              className="glass-card p-5 text-left transition-all duration-200 hover:translate-y-[-2px]"
            >
              <div className="mb-3" style={{ color: "var(--th-accent-text)" }}>
                {f.icon}
              </div>
              <h3 className="text-sm font-semibold mb-1">{f.title}</h3>
              <p className="text-xs leading-relaxed" style={{ color: "var(--th-text-3)" }}>
                {f.desc}
              </p>
            </div>
          ))}
        </div>
      </main>

      {/* Footer */}
      <footer className="py-6 text-center text-xs" style={{ color: "var(--th-text-4)" }}>
        墨灵 Vibe Writing · 选择推进，灵感不中断
      </footer>
    </div>
  );
}
