"use client";

import { memo } from "react";
import { Modal } from "@/components/ui/Modal";
import { Button } from "@/components/ui/Button";
import styles from "./ProjectDetailModal.module.css";
import type { Project } from "@/lib/types";
import { PROJECT_STATUS_LABELS } from "@/lib/constants";

interface ProjectDetailModalProps {
  project: Project | null;
  isOpen: boolean;
  onClose: () => void;
  onEdit?: () => void;
  onDelete?: () => void;
}

function formatWordCount(count: number): string {
  if (count >= 10000) return `${(count / 10000).toFixed(1)}万`;
  if (count >= 1000) return `${(count / 1000).toFixed(1)}k`;
  return `${count}`;
}

export const ProjectDetailModal = memo(function ProjectDetailModal({
  project,
  isOpen,
  onClose,
  onEdit,
  onDelete,
}: ProjectDetailModalProps) {
  if (!project) return null;

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={project.title}
      footer={
        <div className={styles.footer}>
          {onEdit && (
            <Button variant="secondary" onClick={onEdit}>
              编辑
            </Button>
          )}
          {onDelete && (
            <Button variant="danger" onClick={onDelete}>
              删除
            </Button>
          )}
        </div>
      }
    >
      <div className={styles.detail}>
        <div className={styles.row}>
          <span className={styles.label}>作者</span>
          <span className={styles.value}>{project.author}</span>
        </div>
        <div className={styles.row}>
          <span className={styles.label}>类型</span>
          <span className={styles.value}>{project.genre}</span>
        </div>
        <div className={styles.row}>
          <span className={styles.label}>状态</span>
          <span className={styles.value}>
            {PROJECT_STATUS_LABELS[project.status] ?? project.status}
          </span>
        </div>
        <div className={styles.row}>
          <span className={styles.label}>字数</span>
          <span className={styles.value}>{formatWordCount(project.word_count)}</span>
        </div>
        <div className={styles.row}>
          <span className={styles.label}>目标字数</span>
          <span className={styles.value}>
            {project.target_words ? formatWordCount(project.target_words) : "未设置"}
          </span>
        </div>
        <div className={styles.row}>
          <span className={styles.label}>更新频率</span>
          <span className={styles.value}>{project.frequency ?? "未设置"}</span>
        </div>

        {project.tags && project.tags.length > 0 && (
          <div className={styles.tagsSection}>
            <span className={styles.label}>标签</span>
            <div className={styles.tags}>
              {project.tags.map((tag) => (
                <span key={tag} className={styles.tag}>
                  {tag}
                </span>
              ))}
            </div>
          </div>
        )}

        {project.synopsis && (
          <div className={styles.section}>
            <span className={styles.label}>简介</span>
            <p className={styles.text}>{project.synopsis}</p>
          </div>
        )}

        {project.worldview && (
          <div className={styles.section}>
            <span className={styles.label}>世界观</span>
            <p className={styles.text}>{project.worldview}</p>
          </div>
        )}

        {project.protagonist && (
          <div className={styles.row}>
            <span className={styles.label}>主角</span>
            <span className={styles.value}>{project.protagonist}</span>
          </div>
        )}

        <div className={styles.row}>
          <span className={styles.label}>创建时间</span>
          <span className={styles.value}>
            {new Date(project.created_at).toLocaleDateString("zh-CN")}
          </span>
        </div>
        <div className={styles.row}>
          <span className={styles.label}>更新时间</span>
          <span className={styles.value}>
            {new Date(project.updated_at).toLocaleDateString("zh-CN")}
          </span>
        </div>
      </div>
    </Modal>
  );
});
