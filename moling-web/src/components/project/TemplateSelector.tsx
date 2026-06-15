"use client";

import { useState, useEffect } from "react";
import styles from "./TemplateSelector.module.css";
import { templatesApi } from "@/lib/api";
import type { Template } from "@/lib/types";

interface TemplateSelectorProps {
  onSelect: (templateId: string) => void;
}

export function TemplateSelector({ onSelect }: TemplateSelectorProps) {
  const [selected, setSelected] = useState<string | null>(null);
  const [templates, setTemplates] = useState<Template[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchTemplates = async () => {
      try {
        setLoading(true);
        const result = await templatesApi.list();
        setTemplates(result.data || []);
      } catch (err) {
        console.error("Failed to load templates:", err);
        setError("加载模板失败");
      } finally {
        setLoading(false);
      }
    };

    fetchTemplates();
  }, []);

  const handleSelect = (id: string) => {
    setSelected(id);
    onSelect(id);
  };

  if (loading) {
    return <div className={styles.loading}>加载模板中...</div>;
  }

  if (error) {
    return <div className={styles.error}>{error}</div>;
  }

  return (
    <div className={styles.grid}>
      {templates.map((template) => (
        <div
          key={template.id}
          className={`${styles.card} ${selected === template.id ? styles.selected : ""}`}
          onClick={() => handleSelect(template.id)}
        >
          <span className={styles.icon}>{template.icon || "📄"}</span>
          <h4 className={styles.name}>{template.name}</h4>
          <p className={styles.description}>{template.description}</p>
          {template.worldSuggestion && (
            <div className={styles.preview}>
              <p className={styles.previewLabel}>
                <strong>世界观参考：</strong>
                {template.worldSuggestion}
              </p>
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
