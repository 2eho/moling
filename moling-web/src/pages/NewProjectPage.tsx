import { ArrowLeft, BookOpen, FlaskConical, Globe, Sparkles, Swords } from "lucide-react";
import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { persistProject } from "@/db/sync";
import { useWritingStore, type WritingProject } from "@/stores/useWritingStore";

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
    persistProject(project);
    navigate(`/workspace/${project.id}`);
  };

  const inputBase =
    "w-full px-4 py-3 rounded-xl text-sm outline-none transition-all duration-200 bg-th-input border border-th-border-subtle text-th-text";

  return (
    <div className="min-h-screen flex flex-col bg-th-bg text-th-text">
      <header className="flex items-center gap-3 px-6 py-4">
        <Link to="/projects" className="text-th-text-3 hover:text-th-text-2 transition-colors">
          <ArrowLeft size={20} />
        </Link>
        <div className="w-7 h-7 rounded-lg flex items-center justify-center bg-gradient-to-br from-[var(--th-logo-from)] to-[var(--th-logo-to)]">
          <Sparkles size={14} className="text-white" />
        </div>
        <span className="text-base font-bold">新建项目</span>
      </header>

      <main className="flex-1 max-w-lg mx-auto w-full px-6 py-8">
        <form onSubmit={handleCreate} className="flex flex-col gap-5">
          <div>
            <label className="text-sm font-medium mb-2 block text-th-text-2">书名</label>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="给你的作品取个名字..."
              required
              className={inputBase}
            />
          </div>

          <div>
            <label className="text-sm font-medium mb-2 block text-th-text-2">类型</label>
            <div className="grid grid-cols-2 gap-2">
              {GENRES.map((g) => {
                const isSelected = genre === g.id;
                return (
                  <button
                    key={g.id}
                    type="button"
                    onClick={() => setGenre(g.id)}
                    className={`flex flex-col items-center gap-2 p-4 rounded-xl transition-all duration-200 ${
                      isSelected
                        ? "bg-th-accent-dim border border-th-accent"
                        : "bg-th-card border border-th-border-subtle"
                    }`}
                  >
                    <div className={isSelected ? "text-th-accent-text" : "text-th-text-3"}>
                      {g.icon}
                    </div>
                    <span
                      className={`text-xs font-medium ${isSelected ? "text-th-accent-text" : "text-th-text-2"}`}
                    >
                      {g.label}
                    </span>
                  </button>
                );
              })}
            </div>
          </div>

          <div>
            <label className="text-sm font-medium mb-2 block text-th-text-2">
              简介
              <span className="ml-1 font-normal text-th-text-4">选填</span>
            </label>
            <textarea
              value={summary}
              onChange={(e) => setSummary(e.target.value)}
              placeholder="简单描述一下故事..."
              rows={3}
              className={`${inputBase} resize-none`}
            />
          </div>

          <button
            type="submit"
            disabled={!title.trim()}
            className="w-full py-3 rounded-xl text-sm font-semibold text-white bg-gradient-to-br from-[var(--th-logo-from)] to-[var(--th-logo-to)] shadow-[0_4px_20px_var(--th-accent-glow)] transition-all duration-200 disabled:opacity-40 disabled:cursor-not-allowed hover:scale-[1.02] active:scale-[0.98] mt-2"
          >
            创建项目
          </button>
        </form>
      </main>
    </div>
  );
}
