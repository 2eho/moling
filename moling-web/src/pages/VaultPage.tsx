import { useParams, Link } from "react-router-dom";
import { useState } from "react";
import { CharacterLibrary } from "@/components/phase4/CharacterLibrary";
import { TimelineLibrary } from "@/components/phase4/TimelineLibrary";
import { ForeshadowingLibrary } from "@/components/phase4/ForeshadowingLibrary";
import { WorldviewLibrary } from "@/components/phase4/WorldviewLibrary";
import { CardManager } from "@/components/phase4/CardManager";
import { ArrowLeft, Library } from "lucide-react";

type VaultTab = "characters" | "timeline" | "foreshadowing" | "worldview" | "cards";

const TABS: { id: VaultTab; label: string }[] = [
  { id: "characters", label: "角色库" },
  { id: "timeline", label: "时间线" },
  { id: "foreshadowing", label: "承诺库" },
  { id: "worldview", label: "世界观" },
  { id: "cards", label: "卡牌池" },
];

export function VaultPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const [activeTab, setActiveTab] = useState<VaultTab>("characters");

  return (
    <div
      className="min-h-screen flex flex-col"
      style={{ background: "var(--th-bg)", color: "var(--th-text)" }}
    >
      <header
        className="shrink-0 flex items-center gap-3 px-4 py-3 border-b"
        style={{ borderColor: "var(--th-border-subtle)" }}
      >
        <Link
          to={`/workspace/${projectId}`}
          className="p-1.5 rounded-lg transition-colors hover:opacity-80"
          style={{ color: "var(--th-text-3)" }}
        >
          <ArrowLeft size={18} />
        </Link>
        <div className="flex items-center gap-2">
          <Library size={16} style={{ color: "var(--th-accent-text)" }} />
          <h1 className="text-sm font-semibold">四库系统</h1>
        </div>
      </header>

      <nav
        className="shrink-0 flex items-center gap-1 px-4 py-2 border-b overflow-x-auto"
        style={{ borderColor: "var(--th-border-subtle)" }}
      >
        {TABS.map((tab) => {
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className="px-3 py-1.5 rounded-lg text-xs font-medium transition-colors whitespace-nowrap"
              style={{
                background: isActive ? "var(--th-accent-dim)" : "transparent",
                color: isActive ? "var(--th-accent-text)" : "var(--th-text-3)",
              }}
            >
              {tab.label}
            </button>
          );
        })}
      </nav>

      <main className="flex-1 overflow-y-auto px-4 py-5">
        <div className="max-w-4xl mx-auto">
          {activeTab === "characters" && <CharacterLibrary projectId={projectId!} />}
          {activeTab === "timeline" && <TimelineLibrary projectId={projectId!} />}
          {activeTab === "foreshadowing" && <ForeshadowingLibrary projectId={projectId!} />}
          {activeTab === "worldview" && <WorldviewLibrary projectId={projectId!} />}
          {activeTab === "cards" && <CardManager projectId={projectId!} />}
        </div>
      </main>
    </div>
  );
}
