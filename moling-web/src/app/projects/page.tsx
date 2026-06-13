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

  const filteredProjects = projects.filter(
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

  return (
    <div className={styles.container}>
      {/* Header */}
      <div className={styles.header}>
        <div className={styles.headerLeft}>
          <h1 className={styles.greeting}>我的项目</h1>
          <p className={styles.subtitle}>
            欢迎回来，继续你的创作之旅
          </p>
        </div>
        <div className={styles.headerActions}>
          <Input
            placeholder="搜索项目..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
          <Button
            variant="primary"
            size="md"
            onClick={() => router.push("/projects/new")}
          >
            + 新建项目
          </Button>
        </div>
      </div>

      {/* Stats */}
      <div className={styles.statsSection}>
        {isLoading ? (
          <div className={styles.statsSkeleton}>
            {[1, 2, 3, 4].map((i) => (
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
            <span className={styles.emptyIcon}>📚</span>
            <p className={styles.emptyTitle}>暂无项目</p>
            <p className={styles.emptyDesc}>点击"新建项目"开始创作吧</p>
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
            // 保存最后访问的项目ID
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
