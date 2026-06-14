"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useProjects } from "@/hooks/useProjects";
import { CreationModeCard } from "@/components/project/CreationModeCard";
import { TemplateSelector } from "@/components/project/TemplateSelector";
import { ProjectForm } from "@/components/project/ProjectForm";
import { Button } from "@/components/ui/Button";
import { showToast } from "@/components/ui/Toast";
import { CREATION_MODES, TEMPLATES } from "@/lib/constants";
import styles from "./new-project.module.css";

export default function NewProjectPage() {
  const router = useRouter();
  const { createProject } = useProjects();

  const [step, setStep] = useState(1);
  const [mode, setMode] = useState<string | null>(null);
  const [selectedTemplate, setSelectedTemplate] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);

  const handleModeSelect = (modeId: string) => {
    setMode(modeId);
    setStep(2);
  };

  const handleTemplateSelect = (templateId: string) => {
    setSelectedTemplate(templateId);
  };

  const handleNextFromTemplate = () => {
    const template = TEMPLATES.find((t) => t.id === selectedTemplate);
    if (template) {
      setStep(3);
    }
  };

  const handleCreateProject = async (data: Record<string, unknown>) => {
    setCreating(true);
    try {
      const template = TEMPLATES.find((t) => t.id === selectedTemplate);
      const projectData = {
        ...data,
        creation_mode: mode === "from_template" ? "from_scratch" : mode,
        ...(template
          ? {
              genre: template.genre,
              worldview: template.worldSuggestion,
              protagonist: template.protagonistSuggestion,
            }
          : {}),
      };
      const project = await createProject(projectData as any);
      showToast("success", "项目创建成功！");
      router.push(`/workspace/${project.id}`);
    } catch {
      showToast("error", "创建失败，请稍后重试");
    } finally {
      setCreating(false);
    }
  };

  return (
    <div className={styles.container}>
      {/* Step Indicator */}
      <div className={styles.steps}>
        {[1, 2, 3].map((s) => (
          <div
            key={s}
            className={`${styles.step} ${step >= s ? styles.stepActive : ""} ${step === s ? styles.stepCurrent : ""}`}
          >
            <span className={styles.stepNumber}>{s}</span>
            <span className={styles.stepLabel}>
              {s === 1 ? "创作模式" : s === 2 ? "填写信息" : "确认创建"}
            </span>
          </div>
        ))}
      </div>

      {/* Step 1: Creation Mode */}
      {step === 1 && (
        <div className={styles.section}>
          <h2 className={styles.sectionTitle}>选择创作模式</h2>
          <p className={styles.sectionDesc}>
            选择适合你的创作方式
          </p>
          <div className={styles.modeGrid}>
            {CREATION_MODES.map((cm) => (
              <CreationModeCard
                key={cm.id}
                id={cm.id}
                title={cm.title}
                description={cm.description}
                icon={cm.icon}
                selected={mode === cm.id}
                onClick={() => handleModeSelect(cm.id)}
              />
            ))}
          </div>
        </div>
      )}

      {/* Step 2: Template or Form */}
      {step === 2 && mode === "from_template" && (
        <div className={styles.section}>
          <h2 className={styles.sectionTitle}>选择模板</h2>
          <p className={styles.sectionDesc}>
            选择一个预设模板快速开始
          </p>
          <TemplateSelector onSelect={handleTemplateSelect} />
          <div className={styles.actions}>
            <Button
              variant="primary"
              size="lg"
              onClick={handleNextFromTemplate}
              disabled={!selectedTemplate}
            >
              下一步
            </Button>
          </div>
        </div>
      )}

      {step === 2 && mode === "from_scratch" && (
        <div className={styles.section}>
          <h2 className={styles.sectionTitle}>填写项目信息</h2>
          <p className={styles.sectionDesc}>
            设定你的作品基本信息
          </p>
          <ProjectForm
            onSubmit={async (data) => {
              await handleCreateProject(data as any);
            }}
            loading={creating}
          />
        </div>
      )}

      {/* Step 3: Confirm & Create */}
      {step === 3 && (
        <div className={styles.section}>
          <h2 className={styles.sectionTitle}>确认创建</h2>
          <p className={styles.sectionDesc}>
            确认以下信息，开始你的创作之旅
          </p>
          {selectedTemplate && (
            <div className={styles.confirmCard}>
              {(() => {
                const t = TEMPLATES.find((tmpl) => tmpl.id === selectedTemplate);
                return t ? (
                  <>
                    <div className={styles.confirmHeader}>
                      <span className={styles.confirmIcon}>{t.icon}</span>
                      <h3 className={styles.confirmTitle}>{t.name}</h3>
                    </div>
                    <p className={styles.confirmDesc}>{t.description}</p>
                    <div className={styles.confirmDetail}>
                      <p><strong>世界观参考：</strong>{t.worldSuggestion}</p>
                      <p><strong>主角参考：</strong>{t.protagonistSuggestion}</p>
                    </div>
                  </>
                ) : null;
              })()}
            </div>
          )}
          <div className={styles.actions}>
            <Button variant="secondary" size="lg" onClick={() => setStep(2)}>
              上一步
            </Button>
            <Button
              variant="primary"
              size="lg"
              loading={creating}
              onClick={async () => {
                const template = TEMPLATES.find((t) => t.id === selectedTemplate);
                await handleCreateProject({
                  title: template?.name ?? "新项目",
                  genre: template?.genre ?? "未分类",
                  creation_mode: "from_scratch",
                } as any);
              }}
            >
              确认创建
            </Button>
          </div>
        </div>
      )}

      {/* Back to projects */}
      <div className={styles.back}>
        <Button variant="ghost" onClick={() => router.push("/projects")}>
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" style={{marginRight:"4px", verticalAlign:"middle"}}>
            <polyline points="15 18 9 12 15 6"/>
          </svg>
          返回项目列表
        </Button>
      </div>
    </div>
  );
}
