"use client";

import { useWritingStore, type AgentStatus } from "@/stores/useWritingStore";
import { Brain, GitBranch, Users, MessageSquare, PenTool, Globe } from "lucide-react";

const AGENT_ICONS: Record<string, React.ReactNode> = {
  plot: <GitBranch size={14} />,
  character: <Users size={14} />,
  dialogue: <MessageSquare size={14} />,
  style: <PenTool size={14} />,
  world: <Globe size={14} />,
};

export function AgentPanel() {
  const agents = useWritingStore((s) => s.agents);
  const isGenerating = useWritingStore((s) => s.isGenerating);
  const activeCount = agents.filter((a) => a.status === "active" || a.status === "thinking").length;

  return (
    <aside
      className="w-56 shrink-0 flex flex-col gap-2 p-4 h-full overflow-y-auto"
      style={{ borderLeft: "1px solid var(--th-border-subtle)" }}
    >
      <div className="glass-card p-3 mb-1">
        <div className="flex items-center gap-2">
          <Brain size={14} style={{ color: "var(--th-accent-text)" }} />
          <span className="text-[11px] font-medium" style={{ color: "var(--th-text-2)" }}>
            代理系统
          </span>
        </div>
        <div className="flex items-center gap-2 mt-1.5">
          <div className="flex-1 h-1 rounded-full overflow-hidden" style={{ background: "var(--th-hover)" }}>
            <div
              className="h-full rounded-full transition-all duration-500"
              style={{
                width: `${(activeCount / agents.length) * 100}%`,
                background: "linear-gradient(90deg, var(--th-logo-from), var(--th-logo-to))",
              }}
            />
          </div>
          <span className="text-[10px] tabular-nums" style={{ color: "var(--th-text-3)" }}>
            {activeCount}/{agents.length}
          </span>
        </div>
      </div>

      {agents.map((agent) => (
        <AgentItem key={agent.id} agent={agent} />
      ))}

      {isGenerating && (
        <div className="glass-card p-3" style={{ borderColor: "var(--th-accent-dim)" }}>
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 rounded-full agent-pulse" style={{ background: "var(--th-accent-text)" }} />
            <span className="text-[10px]" style={{ color: "var(--th-accent-text)" }}>
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
                    background: "var(--th-accent-text)",
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
    </aside>
  );
}

function AgentItem({ agent }: { agent: AgentStatus }) {
  const statusBg =
    agent.status === "active"
      ? "var(--th-success)"
      : agent.status === "thinking"
        ? "var(--th-warning)"
        : "var(--th-text-4)";

  const statusGlow =
    agent.status === "active"
      ? "0 0 8px var(--th-success)"
      : agent.status === "thinking"
        ? "0 0 8px var(--th-warning)"
        : undefined;

  return (
    <div className="glass-card p-2.5 flex items-center gap-2.5 transition-all duration-200">
      <div
        className={`w-2 h-2 rounded-full ${agent.status === "thinking" ? "agent-pulse" : ""}`}
        style={{ background: statusBg, boxShadow: statusGlow }}
      />

      <div style={{ color: "var(--th-text-3)" }}>
        {AGENT_ICONS[agent.id] ?? <Brain size={14} />}
      </div>

      <div className="flex flex-col min-w-0">
        <span className="text-[10px] font-medium truncate" style={{ color: "var(--th-text-2)" }}>
          {agent.label}
        </span>
        <span className="text-[9px]" style={{ color: "var(--th-text-3)" }}>
          {agent.status === "active" ? "活跃中" : agent.status === "thinking" ? "思考中..." : "待命"}
        </span>
      </div>

      <span className="text-[8px] ml-auto lowercase" style={{ color: "var(--th-text-4)" }}>
        {agent.name}
      </span>
    </div>
  );
}
