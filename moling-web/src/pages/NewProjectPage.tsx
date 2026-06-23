import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { Sparkles, ArrowLeft, BookOpen, Swords, FlaskConical, Globe } from "lucide-react";
import { useWritingStore, type WritingProject } from "@/stores/useWritingStore";
import { persistProject } from "@/db/sync";

const GENRES = [
  { id: "xuanhuan", label: "玄幻修仙", icon: <Swords size={24} /> },
  { id: "scifi", label: "科幻末世", icon: <FlaskConical size={24} /> },
  { id: "dushi", label: "都市生活", icon: <Globe size={24} /> },
  { id: "other", label: "其他类型", icon: <BookOpen size={24} /> },
];

export function NewProjectPage() {
  const navigate = useNavigate();
  const addProject = useWritingStore((s) => s.addProject);
  const [title, setTitle] = useState("");
  const [genre, setGenre] = useState("");
  const [summary, setSummary] = useState("");

  const handleCreate = (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim()) return;

    const project: WritingProject = {
      id: `novel-${Date.now()}`,
      title: title.trim(),
      genre: genre || "other",
      phase: "ideation",
      chapters: [],
      currentChapter: 0,
      totalChapters: 0,
      summary: summary.trim(),
      status: "draft",
      createdAt: new Date().toISOString().split("T")[0],
      updatedAt: new Date().toISOString().split("T")[0],
      characters: [],
      foreshadowing: [],
      worldRules: "",
      styleNotes: "",
    };

    addProject(project);
    persistProject(project); // durable save to SQLite
    navigate(`/workspace/${project.id}`);
  };

  return (
    <div
      className="min-h-screen flex flex-col"
      style={{ background: "var(--th-bg)", color: "var(--th-text)" }}
    >
      <header className="flex items-center gap-3 px-6 py-4">
        <Link to="/projects" style={{ color: "var(--th-text-3)" }}>
          <ArrowLeft size={20} />
        </Link>
        <div
          className="w-7 h-7 rounded-lg flex items-center justify-center"
          style={{
            background: "linear-gradient(135deg, var(--th-logo-from), var(--th-logo-to))",
          }}
        >
          <Sparkles size={14} className="text-white" />
        </div>
        <span className="text-base font-bold">新建项目</span>
      </header>

      <main className="flex-1 max-w-lg mx-auto w-full px-6 py-8">
        <form onSubmit={handleCreate} className="flex flex-col gap-5">
          <div>
            <label className="text-sm font-medium mb-2 block" style={{ color: "var(--th-text-2)" }}>
              书名
            </label>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="给你的作品取个名字..."
              required
              className="w-full px-4 py-3 rounded-xl text-sm outline-none transition-all duration-200"
              style={{
                background: "var(--th-input)",
                border: "1px solid var(--th-border-subtle)",
                color: "var(--th-text)",
              }}
            />
          </div>

          <div>
            <label className="text-sm font-medium mb-2 block" style={{ color: "var(--th-text-2)" }}>
              类型
            </label>
            <div className="grid grid-cols-2 gap-2">
              {GENRES.map((g) => (
                <button
                  key={g.id}
                  type="button"
                  onClick={() => setGenre(g.id)}
                  className="flex flex-col items-center gap-2 p-4 rounded-xl transition-all duration-200"
                  style={{
                    background: genre === g.id ? "var(--th-accent-dim)" : "var(--th-card)",
                    border: genre === g.id ? "1px solid var(--th-accent)" : "1px solid var(--th-border-subtle)",
                  }}
                >
                  <div style={{ color: genre === g.id ? "var(--th-accent-text)" : "var(--th-text-3)" }}>
                    {g.icon}
                  </div>
                  <span
                    className="text-xs font-medium"
                    style={{ color: genre === g.id ? "var(--th-accent-text)" : "var(--th-text-2)" }}
                  >
                    {g.label}
                  </span>
                </button>
              ))}
            </div>
          </div>

          <div>
            <label className="text-sm font-medium mb-2 block" style={{ color: "var(--th-text-2)" }}>
              简介
              <span className="ml-1 font-normal" style={{ color: "var(--th-text-4)" }}>选填</span>
            </label>
            <textarea
              value={summary}
              onChange={(e) => setSummary(e.target.value)}
              placeholder="简单描述一下故事..."
              rows={3}
              className="w-full px-4 py-3 rounded-xl text-sm outline-none resize-none transition-all duration-200"
              style={{
                background: "var(--th-input)",
                border: "1px solid var(--th-border-subtle)",
                color: "var(--th-text)",
              }}
            />
          </div>

          <button
            type="submit"
            disabled={!title.trim()}
            className="w-full py-3 rounded-xl text-sm font-semibold transition-all duration-200 disabled:opacity-40 disabled:cursor-not-allowed hover:scale-[1.02] active:scale-[0.98] mt-2"
            style={{
              background: "linear-gradient(135deg, var(--th-logo-from), var(--th-logo-to))",
              color: "#fff",
              boxShadow: "0 4px 20px var(--th-accent-glow)",
            }}
          >
            创建项目
          </button>
        </form>
      </main>
    </div>
  );
}
