import { ArrowRight, BookOpen, Brain, GitBranch, Sparkles, Zap } from "lucide-react";
import { Link } from "react-router-dom";

const features = [
  {
    icon: <Brain size={22} />,
    title: "Agent 协作",
    desc: "Plot / Character / Dialogue / Style / World — 五 Agent 并行分析，多维度护航",
  },
  {
    icon: <GitBranch size={22} />,
    title: "A/B/C 选项推进",
    desc: "每次决策三个方向 + 自由输入，点击即推进，灵感永不中断",
  },
  {
    icon: <BookOpen size={22} />,
    title: "四库系统",
    desc: "角色库 / 情节承诺库 / 世界观库 / 伏笔钩子库 — 自动追踪，贯穿全书",
  },
];

export function LandingPage() {
  return (
    <div className="min-h-screen flex flex-col bg-th-bg text-th-text">
      {/* Nav — frosted glass */}
      <nav className="sticky top-0 z-50 flex items-center justify-between px-6 py-4 backdrop-blur-xl bg-th-bg/80 border-b border-th-border-subtle">
        <div className="flex items-center gap-2.5">
          <div className="w-9 h-9 rounded-xl flex items-center justify-center bg-gradient-to-br from-[var(--th-logo-from)] to-[var(--th-logo-to)] shadow-[0_2px_16px_var(--th-accent-glow)]">
            <Sparkles size={17} className="text-white" />
          </div>
          <span className="text-lg font-bold tracking-tight">墨灵</span>
        </div>
        <div className="flex items-center gap-2">
          <Link
            to="/auth"
            className="px-5 py-2.5 rounded-xl text-sm font-medium text-th-text-2 hover:text-th-text hover:bg-th-hover transition-all duration-200"
          >
            登录
          </Link>
          <Link
            to="/auth?mode=register"
            className="px-5 py-2.5 rounded-xl text-sm font-semibold text-white bg-gradient-to-br from-[var(--th-logo-from)] to-[var(--th-logo-to)] shadow-[0_2px_12px_var(--th-accent-glow)] hover:shadow-[0_4px_20px_var(--th-accent-glow)] transition-all duration-300 active:scale-[0.97]"
          >
            免费开始
          </Link>
        </div>
      </nav>

      {/* Hero */}
      <main className="flex-1 flex flex-col items-center justify-center px-6 py-20 text-center">
        {/* Badge */}
        <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full mb-10 text-xs font-medium bg-th-accent-dim text-th-accent-text border border-th-accent-dim/30">
          <Zap size={12} className="text-[var(--th-accent)]" />
          Agent of Agents · Heavy Options, Light Input
        </div>

        <h1 className="text-5xl md:text-6xl font-bold mb-5 tracking-tight leading-[1.15] max-w-2xl">
          <span className="text-th-text">AI 驱动的</span>
          <br />
          <span className="bg-gradient-to-r from-[var(--th-logo-from)] via-[var(--th-accent)] to-[var(--th-logo-to)] bg-clip-text text-transparent">
            网文创作引擎
          </span>
        </h1>

        <p className="text-base md:text-lg max-w-xl mb-12 leading-relaxed text-th-text-3">
          告别空白页面的恐惧。墨灵用 A/B/C 选项引导创作方向，五个 AI Agent 为每个章节保驾护航。
        </p>

        <Link
          to="/auth?mode=register"
          className="group inline-flex items-center gap-2.5 px-8 py-4 rounded-2xl text-base font-semibold text-white bg-gradient-to-br from-[var(--th-logo-from)] to-[var(--th-logo-to)] shadow-[0_4px_24px_var(--th-accent-glow)] hover:shadow-[0_6px_32px_var(--th-accent-glow)] hover:scale-[1.03] active:scale-[0.97] transition-all duration-300"
        >
          <Sparkles size={18} />
          开始创作
          <ArrowRight
            size={18}
            className="group-hover:translate-x-1 transition-transform duration-300"
          />
        </Link>

        {/* Feature Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-5 mt-20 max-w-4xl w-full">
          {features.map((f) => (
            <div
              key={f.title}
              className="group glass-card p-6 text-left transition-all duration-300 hover:-translate-y-1 hover:shadow-[0_8px_30px_rgba(0,0,0,0.12)]"
            >
              <div className="w-10 h-10 rounded-xl flex items-center justify-center mb-4 bg-th-accent-dim text-th-accent-text group-hover:scale-110 transition-transform duration-300">
                {f.icon}
              </div>
              <h3 className="text-base font-semibold mb-2 text-th-text">{f.title}</h3>
              <p className="text-sm leading-relaxed text-th-text-3">{f.desc}</p>
            </div>
          ))}
        </div>
      </main>

      {/* Footer */}
      <footer className="py-8 text-center text-xs text-th-text-4 border-t border-th-border-subtle">
        墨灵 Vibe Writing · 选择推进，灵感不中断
      </footer>
    </div>
  );
}
