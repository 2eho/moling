"use client";

import { useState } from "react";
import { Input } from "@/components/ui/Input";
import { Button } from "@/components/ui/Button";
import styles from "./ProjectForm.module.css";
import { GENRE_OPTIONS } from "@/lib/constants";
import type { Project } from "@/lib/types";

interface ProjectFormProps {
  initialData?: Partial<Project>;
  onSubmit: (data: Partial<Project>) => Promise<void>;
  loading?: boolean;
}

export function ProjectForm({ initialData, onSubmit, loading }: ProjectFormProps) {
  const [title, setTitle] = useState(initialData?.title ?? "");
  const [author, setAuthor] = useState(initialData?.author ?? "墨灵用户");
  const [genre, setGenre] = useState(initialData?.genre ?? GENRE_OPTIONS[0]);
  const [tags, setTags] = useState(initialData?.tags?.join(", ") ?? "");
  const [synopsis, setSynopsis] = useState(initialData?.synopsis ?? "");
  const [worldview, setWorldview] = useState(initialData?.worldview ?? "");
  const [protagonist, setProtagonist] = useState(initialData?.protagonist ?? "");
  const [targetWords, setTargetWords] = useState(
    initialData?.target_words?.toString() ?? "100000",
  );
  const [frequency, setFrequency] = useState(initialData?.frequency ?? "不定期");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    await onSubmit({
      title,
      author,
      genre,
      tags: tags
        .split(/[,，]/)
        .map((t) => t.trim())
        .filter(Boolean),
      synopsis,
      worldview,
      protagonist,
      target_words: parseInt(targetWords, 10) || 0,
      frequency,
    });
  };

  return (
    <form className={styles.form} onSubmit={handleSubmit}>
      <div className={styles.grid}>
        <Input
          label="作品标题"
          placeholder="输入作品标题"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          required
        />

        <Input
          label="作者"
          placeholder="输入作者名"
          value={author}
          onChange={(e) => setAuthor(e.target.value)}
        />
      </div>

      <div className={styles.grid}>
        <div className={styles.field}>
          <label className={styles.fieldLabel}>类型</label>
          <select
            className={styles.select}
            value={genre}
            onChange={(e) => setGenre(e.target.value)}
          >
            {GENRE_OPTIONS.map((g) => (
              <option key={g} value={g}>
                {g}
              </option>
            ))}
          </select>
        </div>

        <Input
          label="标签（逗号分隔）"
          placeholder="如：仙侠, 冒险"
          value={tags}
          onChange={(e) => setTags(e.target.value)}
        />
      </div>

      <div className={styles.field}>
        <label className={styles.fieldLabel}>简介</label>
        <textarea
          className={styles.textarea}
          placeholder="用几句话概括你的作品"
          value={synopsis}
          onChange={(e) => setSynopsis(e.target.value)}
          rows={3}
        />
      </div>

      <div className={styles.field}>
        <label className={styles.fieldLabel}>世界观设定</label>
        <textarea
          className={styles.textarea}
          placeholder="描述你的世界设定、规则和背景"
          value={worldview}
          onChange={(e) => setWorldview(e.target.value)}
          rows={3}
        />
      </div>

      <div className={styles.grid}>
        <Input
          label="主角"
          placeholder="主角名称"
          value={protagonist}
          onChange={(e) => setProtagonist(e.target.value)}
        />

        <Input
          label="目标字数"
          type="number"
          value={targetWords}
          onChange={(e) => setTargetWords(e.target.value)}
        />
      </div>

      <div className={styles.field}>
        <label className={styles.fieldLabel}>更新频率</label>
        <select
          className={styles.select}
          value={frequency}
          onChange={(e) => setFrequency(e.target.value)}
        >
          <option value="每日更新">每日更新</option>
          <option value="每周三更">每周三更</option>
          <option value="每周两更">每周两更</option>
          <option value="每周一更">每周一更</option>
          <option value="不定期">不定期</option>
        </select>
      </div>

      <Button type="submit" variant="primary" size="lg" fullWidth loading={loading}>
        创建项目
      </Button>
    </form>
  );
}
