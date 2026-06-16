"use client";

import { useState } from "react";
import { Input } from "@/components/ui/Input";
import { Button } from "@/components/ui/Button";
import { FormError, FieldError } from "@/components/FormError";
import { validateForm, clearFieldError, parseApiError } from "@/lib/formValidation";
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
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [apiError, setApiError] = useState("");

  const validationRules = {
    title: [
      { required: true, message: '作品书名不能为空' },
      { min: 2, message: '作品书名至少2个字符' },
      { max: 100, message: '作品书名最多100个字符' }
    ],
    genre: [
      { required: true, message: '请选择作品类型' }
    ]
  };

  const handleFieldChange = (field: string, value: string) => {
    setErrors(prev => clearFieldError(prev, field));
    setApiError("");
    
    switch (field) {
      case 'title': setTitle(value); break;
      case 'author': setAuthor(value); break;
      case 'genre': setGenre(value); break;
      case 'tags': setTags(value); break;
      case 'synopsis': setSynopsis(value); break;
      case 'worldview': setWorldview(value); break;
      case 'protagonist': setProtagonist(value); break;
      case 'targetWords': setTargetWords(value); break;
      case 'frequency': setFrequency(value); break;
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setApiError("");
    
    const formData = {
      title,
      author,
      genre,
      tags,
      synopsis,
      worldview,
      protagonist,
      target_words: parseInt(targetWords, 10) || 0,
      frequency,
    };
    
    const validationErrors = validateForm(formData, validationRules);
    if (Object.keys(validationErrors).length > 0) {
      setErrors(validationErrors);
      return;
    }
    
    try {
      await onSubmit({
        title,
        author,
        genre,
        tags: tags
          .split(/[,，]/)
          .map((t: string) => t.trim())
          .filter(Boolean),
        synopsis,
        worldview,
        protagonist,
        target_words: parseInt(targetWords, 10) || 0,
        frequency,
      });
    } catch (error: any) {
      // 解析API错误，显示具体信息
      const parsed = parseApiError(error);
      setApiError(parsed.message);
      if (parsed.errors) {
        setErrors(parsed.errors);
      }
    }
  };

  return (
    <form className={styles.form} onSubmit={handleSubmit}>
      {/* API级别错误提示 */}
      <FormError error={apiError} errors={errors} />
      
      <div className={styles.grid}>
        <div className={styles.field}>
          <label className={styles.fieldLabel}>
            作品标题 <span className={styles.required}>*</span>
          </label>
          <Input
            placeholder="输入作品标题"
            value={title}
            onChange={(e) => handleFieldChange('title', e.target.value)}
            error={errors.title}
          />
          <FieldError error={errors.title} />
        </div>

        <div className={styles.field}>
          <label className={styles.fieldLabel}>作者</label>
          <Input
            placeholder="输入作者名"
            value={author}
            onChange={(e) => handleFieldChange('author', e.target.value)}
          />
        </div>
      </div>

      <div className={styles.grid}>
        <div className={styles.field}>
          <label className={styles.fieldLabel}>
            类型 <span className={styles.required}>*</span>
          </label>
          <select
            className={styles.select}
            value={genre}
            onChange={(e) => handleFieldChange('genre', e.target.value)}
          >
            {GENRE_OPTIONS.map((g) => (
              <option key={g} value={g}>
                {g}
              </option>
            ))}
          </select>
          <FieldError error={errors.genre} />
        </div>

        <div className={styles.field}>
          <label className={styles.fieldLabel}>标签（逗号分隔）</label>
          <Input
            placeholder="如：仙侠, 冒险"
            value={tags}
            onChange={(e) => handleFieldChange('tags', e.target.value)}
          />
        </div>
      </div>

      <div className={styles.field}>
        <label className={styles.fieldLabel}>简介</label>
        <textarea
          className={styles.textarea}
          placeholder="用几句话概括你的作品"
          value={synopsis}
          onChange={(e) => handleFieldChange('synopsis', e.target.value)}
          rows={3}
        />
      </div>

      <div className={styles.field}>
        <label className={styles.fieldLabel}>世界观设定</label>
        <textarea
          className={styles.textarea}
          placeholder="描述你的世界设定、规则和背景"
          value={worldview}
          onChange={(e) => handleFieldChange('worldview', e.target.value)}
          rows={3}
        />
      </div>

      <div className={styles.grid}>
        <div className={styles.field}>
          <label className={styles.fieldLabel}>主角</label>
          <Input
            placeholder="主角名称"
            value={protagonist}
            onChange={(e) => handleFieldChange('protagonist', e.target.value)}
          />
        </div>

        <div className={styles.field}>
          <label className={styles.fieldLabel}>目标字数</label>
          <Input
            type="number"
            value={targetWords}
            onChange={(e) => handleFieldChange('targetWords', e.target.value)}
          />
        </div>
      </div>

      <div className={styles.field}>
        <label className={styles.fieldLabel}>更新频率</label>
        <select
          className={styles.select}
          value={frequency}
          onChange={(e) => handleFieldChange('frequency', e.target.value)}
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
