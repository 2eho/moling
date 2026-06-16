"use client";

import { useParams, useRouter } from "next/navigation";
import { useState, useEffect } from "react";
import { Input } from "@/components/ui/Input";
import { Button } from "@/components/ui/Button";
import { showToast } from "@/components/ui/Toast";
import { projectApi } from "@/lib/api";
import type { Project } from "@/lib/types";
import { safeObject } from "@/lib/apiSafety";  // ✅ 导入安全工具
import styles from "./edit.module.css";

export default function EditProjectPage() {
  const params = useParams();
  const router = useRouter();
  const projectId = params.projectId as string;
  const [project, setProject] = useState<Project | null>(null);
  const [title, setTitle] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    projectApi
      .getById(projectId)
      .then((res) => {
        // ✅ 修复：使用 safeObject 确保 project 不会是 undefined
        const projectData = safeObject<Project>(res.data, null);
        
        if (!projectData) {
          showToast("error", "项目不存在");
          router.push("/projects");
          return;
        }
        
        setProject(projectData);
        setTitle(projectData.title || "");
      })
      .catch(() => showToast("error", "加载项目信息失败"))
      .finally(() => setLoading(false));
  }, [projectId, router]);

  const handleSave = async () => {
    if (!title.trim()) {
      showToast("warning", "请输入项目名称");
      return;
    }
    setSaving(true);
    try {
      await projectApi.update(projectId, { title: title.trim() } as Partial<Project>);
      showToast("success", "保存成功");
      router.push(`/workspace/${projectId}`);
    } catch {
      showToast("error", "保存失败，请稍后重试");
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return <div className={styles.container}><div className={styles.loading}>加载中...</div></div>;
  }

  return (
    <div className={styles.container}>
      <div className={styles.card}>
        <h1 className={styles.title}>编辑项目</h1>
        <div className={styles.field}>
          <label className={styles.label}>项目名称</label>
          <Input
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="输入项目名称"
          />
        </div>
        <div className={styles.actions}>
          <Button variant="ghost" onClick={() => router.back()}>取消</Button>
          <Button variant="primary" onClick={handleSave} disabled={saving}>
            {saving ? "保存中..." : "保存"}
          </Button>
        </div>
      </div>
    </div>
  );
}
