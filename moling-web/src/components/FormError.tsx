"use client";

import styles from "./FormError.module.css";

export interface FormErrorProps {
  /** 单个错误信息字符串 */
  error?: string;
  /** 多字段错误对象（来自 validateForm） */
  errors?: Record<string, string>;
  /** 是否显示（默认 true） */
  show?: boolean;
  /** 警告样式（默认 danger） */
  variant?: "danger" | "warning";
}

/**
 * 表单错误提示组件
 * - 支持显示单个错误信息
 * - 支持显示多个字段错误（对象）
 * - 使用 Alert 样式
 * - 可被所有表单页面复用
 */
export function FormError({
  error,
  errors,
  show = true,
  variant = "danger",
}: FormErrorProps) {
  if (!show) return null;

  const hasError = error || (errors && Object.keys(errors).length > 0);
  if (!hasError) return null;

  const variantClass = variant === "warning" ? styles.warning : styles.danger;

  return (
    <div className={styles.container} role="alert">
      {/* 单个错误信息 */}
      {error && (
        <div className={`${styles.alert} ${variantClass}`}>
          <span className={styles.icon}>⚠</span>
          <span className={styles.message}>{error}</span>
        </div>
      )}

      {/* 多字段错误列表 */}
      {errors && Object.keys(errors).length > 0 && (
        <div className={`${styles.alert} ${variantClass}`}>
          <span className={styles.icon}>⚠</span>
          <ul className={styles.fieldList}>
            {Object.entries(errors).map(([field, msg]) => (
              <li key={field} className={styles.fieldItem}>
                <span className={styles.fieldDot} />
                <span className={styles.message}>{msg}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

export interface FieldErrorProps {
  /** 该字段的错误信息（空则不显示） */
  error?: string;
}

/**
 * 单字段行内错误提示（用于表单项下方）
 */
export function FieldError({ error }: FieldErrorProps) {
  if (!error) return null;
  return (
    <p className={styles.inlineError} role="alert">
      {error}
    </p>
  );
}
