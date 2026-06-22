import { useParams, Link } from "react-router-dom";
import { Phase4TaskPanel } from "@/components/phase4/Phase4TaskPanel";
import { ArrowLeft, GitBranch } from "lucide-react";

export function Phase4TasksPage() {
  const { projectId } = useParams<{ projectId: string }>();

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
          <GitBranch size={16} style={{ color: "var(--th-accent-text)" }} />
          <h1 className="text-sm font-semibold">Phase 4 任务历史</h1>
        </div>
      </header>

      <main className="flex-1 overflow-y-auto px-4 py-5">
        <div className="max-w-3xl mx-auto">
          <Phase4TaskPanel projectId={projectId!} />
        </div>
      </main>
    </div>
  );
}
