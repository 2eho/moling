"use client";

import { useState } from "react";
import styles from "./TemplateSelector.module.css";
import { TEMPLATES } from "@/lib/constants";

interface TemplateSelectorProps {
  onSelect: (templateId: string) => void;
}

export function TemplateSelector({ onSelect }: TemplateSelectorProps) {
  const [selected, setSelected] = useState<string | null>(null);

  const handleSelect = (id: string) => {
    setSelected(id);
    onSelect(id);
  };

  return (
    <div className={styles.grid}>
      {TEMPLATES.map((template) => (
        <div
          key={template.id}
          className={`${styles.card} ${selected === template.id ? styles.selected : ""}`}
          onClick={() => handleSelect(template.id)}
        >
          <span className={styles.icon}>{template.icon}</span>
          <h4 className={styles.name}>{template.name}</h4>
          <p className={styles.description}>{template.description}</p>
          <div className={styles.preview}>
            <p className={styles.previewLabel}>
              <strong>世界观参考：</strong>
              {template.worldSuggestion}
            </p>
          </div>
        </div>
      ))}
    </div>
  );
}
