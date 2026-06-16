"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useProjects } from "@/hooks/useProjects";
import { ProjectStats } from "@/components/project/ProjectStats";
import { ProjectCard } from "@/components/project/ProjectCard";
import { ProjectDetailModal } from "@/components/project/ProjectDetailModal";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Modal } from "@/components/ui/Modal";
import { Skeleton } from "@/components/ui/Skeleton";
import type { Project } from "@/lib/types";
import styles from "./projects.module.css";

export default function ProjectsPage() {
  const router = useRouter();
  const { projects, stats, isLoading, deleteProject } = useProjects();
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedProject, setSelectedProject] = useState<Project | null>(null);
  const [deleteConfirmId, setDeleteConfirmId] = useState<string | null>(null);

  // ✅ 防御性检查：确保 projects 始终是数组
  const safeProjects = Array.isArray(projects) ? projects : [];
  const filteredProjects = safeProjects.filter(
    (p) =>
      p.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      p.genre.includes(searchQuery),
  );

  const handleDelete = async () => {
    if (!deleteConfirmId) return;
    await deleteProject(deleteConfirmId);
    setDeleteConfirmId(null);
    setSelectedProject(null);
  };

  const handleNewProject = () => {
    router.push("/projects/new");
  };

  return (
    <div className={styles.container}>
      {/* Header */}
      <div className={styles.header}>
        <div className={styles.headerLeft}>
          <h1 className={styles.greeting}>我的作品</h1>
          <p className={styles.subtitle}>
            欢迎回来，继续你的创作之旅
          </p>
        </div>
        <div className={styles.headerActions}>
          <Input
            placeholder="搜索作品名称..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
          <Button
            variant="primary"
            size="md"
            onClick={handleNewProject}
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" style={{marginRight:"6px"}}>
              <line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/>
            </svg>
            新建作品
          </Button>
        </div>
      </div>

      {/* Stats */}
      <div className={styles.statsSection}>
        {isLoading ? (
          <div className={styles.statsSkeleton}>
            {[1, 2, 3].map((i) => (
              <Skeleton key={i} height={80} borderRadius={12} />
            ))}
          </div>
        ) : (
          <ProjectStats stats={stats} isLoading={isLoading} />
        )}
      </div>

      {/* Project Grid */}
      <div className={styles.grid}>
        {isLoading
          ? [1, 2, 3, 4, 5, 6].map((i) => (
              <Skeleton key={i} height={200} borderRadius={12} />
            ))
          : filteredProjects.map((project) => (
              <ProjectCard
                key={project.id}
                project={project}
                onClick={() => {
                  setSelectedProject(project);
                }}
              />
            ))}
        {!isLoading && filteredProjects.length === 0 && (
          <div className={styles.empty}>
            <svg className={styles.emptyIcon} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
              <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/>
              <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/>
              <line x1="8" y1="11" x2="14" y2="11"/>
            </svg>
            <p className={styles.emptyTitle}>暂无作品</p>
            <p className={styles.emptyDesc}>点击"新建作品"开始创作吧</p>
          </div>
        )}
      </div>

      {/* Detail Modal */}
      <ProjectDetailModal
        project={selectedProject}
        isOpen={!!selectedProject && !deleteConfirmId}
        onClose={() => setSelectedProject(null)}
        onEdit={() => {
          if (selectedProject) {
            localStorage.setItem("lastProjectId", selectedProject.id);
            router.push(`/workspace/${selectedProject.id}`);
          }
        }}
        onDelete={() => {
          if (selectedProject) {
            setDeleteConfirmId(selectedProject.id);
          }
        }}
      />

      {/* Delete Confirmation */}
      <Modal
        isOpen={!!deleteConfirmId}
        onClose={() => setDeleteConfirmId(null)}
        title="确认删除"
        footer={
          <div className={styles.deleteFooter}>
            <Button
              variant="secondary"
              onClick={() => setDeleteConfirmId(null)}
            >
              取消
            </Button>
            <Button variant="danger" onClick={handleDelete}>
              确认删除
            </Button>
          </div>
        }
      >
        <p className={styles.deleteText}>
          确定要删除此项目吗？此操作不可撤销，所有章节内容和数据将被永久删除。
        </p>
      </Modal>
    </div>
  );
}
