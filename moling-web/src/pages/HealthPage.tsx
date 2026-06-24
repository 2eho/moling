import { Activity, ArrowLeft } from "lucide-react";
import { Link, useParams } from "react-router-dom";
import { HealthDashboard } from "@/components/health/HealthDashboard";

export function HealthPage() {
  const { projectId } = useParams<{ projectId: string }>();

  return (
    <div className="min-h-screen flex flex-col bg-th-bg text-th-text">
      <header className="shrink-0 flex items-center gap-3 px-4 py-3 border-b border-th-border-subtle">
        <Link
          to={`/workspace/${projectId}`}
          className="p-1.5 rounded-lg transition-colors hover:opacity-80 text-th-text-3"
        >
          <ArrowLeft size={18} />
        </Link>
        <div className="flex items-center gap-2">
          <Activity size={16} className="text-th-accent-text" />
          <h1 className="text-sm font-semibold">健康监控仪表盘</h1>
        </div>
      </header>

      <main className="flex-1 overflow-y-auto px-4 py-5">
        <div className="max-w-4xl mx-auto">
          <HealthDashboard projectId={projectId!} />
        </div>
      </main>
    </div>
  );
}
