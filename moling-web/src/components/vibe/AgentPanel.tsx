"use client";

import { useWritingStore, type AgentStatus } from "@/stores/useWritingStore";
import {
  Brain,
  GitBranch,
  Users,
  MessageSquare,
  PenTool,
  Globe,
  X,
  Sparkles,
  Activity,
  Clock,
} from "lucide-react";

const AGENT_META: Record<
  string,
  { icon: React.ReactNode; role: string; color: string }
> = {
  plot: {
    icon: <GitBranch size={14} />,
    role: "叙事架构师",
    color: "var(--th-accent-text)",
  },
  character: {
    icon: <Users size={14} />,
    role: "人物设计师",
    color: "var(--th-success)",
  },
  dialogue: {
    icon: <MessageSquare size={14} />,
    role: "对话导演",
    color: "var(--th-warning)",
  },
  style: {
    icon: <PenTool size={14} />,
    role: "风格顾问",
    color: "var(--th-accent)",
  },
  world: {
    icon: <Globe size={14} />,
    role: "世界构建师",
    color: "var(--th-logo-to)",
  },
};

interface AgentPanelProps {
  onClose?: () => void;
}

export function AgentPanel({ onClose }: AgentPanelProps) {
  const agents = useWritingStore((s) => s.agents);
  const isGenerating = useWritingStore((s) => s.isGenerating);
  const activeCount = agents.filter(
    (a) => a.status === "active" || a.status === "thinking"
  ).length;
  const thinkingCount = agents.filter((a) => a.status === "thinking").length;

  return (
    <aside
      className="shrink-0 flex flex-col h-full transition-all duration-300 border-l overflow-hidden"
      style={{
        width: 260,
        borderColor: "var(--th-border-subtle)",
        background: "var(--th-card)",
      }}
    >
      {/* ================================================================
          Header — Agent of Agents
          ================================================================ */}
      <div
        className="flex items-center justify-between px-4 py-3 border-b"
        style={{ borderColor: "var(--th-border-subtle)" }}
      >
        <div className="flex items-center gap-2 min-w-0">
          <Brain
            size={15}
            style={{ color: "var(--th-accent-text)" }}
            className="shrink-0"
          />
          <span
            className="text-[11px] font-semibold tracking-wide uppercase"
            style={{ color: "var(--th-text-2)" }}
          >
            Agent 调度中心
          </span>
        </div>
        {onClose && (
          <button
            onClick={onClose}
            className="p-1 rounded transition-colors hover:opacity-80"
            style={{ color: "var(--th-text-3)" }}
            aria-label="关闭右栏"
          >
            <X size={14} />
          </button>
        )}
      </div>

      {/* ================================================================
          Body — scrollable
          ================================================================ */}
      <div className="flex-1 overflow-y-auto p-3 flex flex-col gap-2">
        {/* ---- 全局状态卡 ---- */}
        <div
          className="rounded-lg p-3"
          style={{
            background: "var(--th-accent-dim)",
            border: "1px solid var(--th-accent-dim)",
          }}
        >
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-1.5">
              <Sparkles size={11} style={{ color: "var(--th-accent-text)" }} />
              <span
                className="text-[10px] font-medium"
                style={{ color: "var(--th-accent-text)" }}
              >
                {isGenerating ? "协作进行中" : "待命中"}
              </span>
            </div>
            <span
              className="text-[9px] font-medium tabular-nums"
              style={{ color: "var(--th-accent-text)" }}
            >
              {activeCount} / {agents.length}
            </span>
          </div>

          {/* 进度条 */}
          <div className="mt-2 flex items-center gap-2">
            <div
              className="flex-1 h-1.5 rounded-full overflow-hidden"
              style={{ background: "var(--th-hover)" }}
            >
              <div
                className="h-full rounded-full transition-all duration-500"
                style={{
                  width: `${(activeCount / agents.length) * 100}%`,
                  background: "linear-gradient(90deg, var(--th-logo-from), var(--th-logo-to))",
                }}
              />
            </div>
          </div>

          {/* 微型状态摘要 */}
          <div className="flex items-center gap-3 mt-2 text-[9px]">
            <span className="flex items-center gap-1" style={{ color: "var(--th-success)" }}>
              <Activity size={9} />
              活跃 {activeCount - thinkingCount}
            </span>
            <span className="flex items-center gap-1" style={{ color: "var(--th-warning)" }}>
              <Clock size={9} />
              思考 {thinkingCount}
            </span>
          </div>
        </div>

        {/* ---- 各 Agent 卡片 ---- */}
        <div
          className="text-[9px] font-semibold tracking-wider uppercase px-1 mt-1"
          style={{ color: "var(--th-text-4)" }}
        >
          代理成员
        </div>

        {agents.map((agent) => (
          <AgentItem key={agent.id} agent={agent} />
        ))}

        {/* ---- 生成脉冲条 ---- */}
        {isGenerating && (
          <div
            className="rounded-lg p-3 mt-1"
            style={{
              border: "1px solid var(--th-accent-dim)",
              background: "var(--th-bg)",
            }}
          >
            <div className="flex items-center gap-2">
              <div
                className="w-2 h-2 rounded-full agent-pulse"
                style={{ background: "var(--th-accent-text)" }}
              />
              <span
                className="text-[10px] font-medium"
                style={{ color: "var(--th-accent-text)" }}
              >
                Agent 协作中...
              </span>
            </div>
            <div className="mt-2 flex gap-1">
              {[0, 1, 2].map((i) => (
                <div
                  key={i}
                  className="flex-1 h-[2px] rounded-full overflow-hidden"
                  style={{ background: "var(--th-accent-dim)" }}
                >
                  <div
                    className="h-full rounded-full"
                    style={{
                      background: "linear-gradient(90deg, var(--th-logo-from), var(--th-logo-to))",
                      animation: "pulse-dot 1.4s ease-in-out infinite",
                      animationDelay: `${i * 0.2}s`,
                      width: "60%",
                    }}
                  />
                </div>
              ))}
            </div>
          </div>
        )}

        {/* ---- 选中提示 ---- */}
        <div
          className="rounded-lg p-2.5 mt-1"
          style={{ background: "var(--th-bg)" }}
        >
          <p
            className="text-[9px] leading-relaxed"
            style={{ color: "var(--th-text-4)" }}
          >
            左侧选择章节 → Agent 自动分析上下文
            <br />
            中央展示 A/B/C 选项 → 点击推进创作
          </p>
        </div>
      </div>
    </aside>
  );
}

function AgentItem({ agent }: { agent: AgentStatus }) {
  const meta = AGENT_META[agent.id] ?? {
    icon: <Brain size={14} />,
    role: "代理",
    color: "var(--th-text-2)",
  };

  const statusBg =
    agent.status === "active"
      ? "var(--th-success)"
      : agent.status === "thinking"
        ? "var(--th-warning)"
        : "var(--th-text-4)";

  const statusGlow =
    agent.status === "active"
      ? `0 0 6px var(--th-success)`
      : agent.status === "thinking"
        ? `0 0 6px var(--th-warning)`
        : undefined;

  const statusLabel =
    agent.status === "active"
      ? "活跃"
      : agent.status === "thinking"
        ? "思考中"
        : "待命";

  const cardBorder =
    agent.status === "active"
      ? "0 0 0 1px var(--th-success) inset"
      : agent.status === "thinking"
        ? "0 0 0 1px var(--th-warning) inset"
        : "none";

  return (
    <div
      className="rounded-lg p-2.5 transition-all duration-200 flex flex-col gap-1.5"
      style={{
        background: agent.status !== "idle" ? "var(--th-hover)" : "var(--th-bg)",
        boxShadow: cardBorder,
      }}
    >
      {/* Top row: icon + label + status dot */}
      <div className="flex items-center gap-2">
        <div style={{ color: meta.color }} className="shrink-0">
          {meta.icon}
        </div>
        <span
          className="text-[10px] font-medium flex-1 truncate"
          style={{ color: "var(--th-text-2)" }}
        >
          {agent.label}
        </span>
        <div className="flex items-center gap-1.5">
          <span
            className="text-[8px] font-medium"
            style={{ color: statusBg }}
          >
            {statusLabel}
          </span>
          <div
            className={`w-1.5 h-1.5 rounded-full shrink-0 ${
              agent.status === "thinking" ? "agent-pulse" : ""
            }`}
            style={{ background: statusBg, boxShadow: statusGlow }}
          />
        </div>
      </div>

      {/* Bottom row: role description */}
      <div className="flex items-center gap-2">
        <div className="w-3.5" /> {/* alignment spacer */}
        <span
          className="text-[9px] truncate"
          style={{ color: "var(--th-text-3)" }}
        >
          {meta.role} · {agent.name}
        </span>
      </div>
    </div>
  );
}
