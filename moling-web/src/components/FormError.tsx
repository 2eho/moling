/**
 * 统一错误提示组件
 * 
 * 显示表单验证错误和API调用错误
 */

import styles from './FormError.module.css';

export interface FormErrorProps {
  /** API级别的错误信息（如"创建项目失败"） */
  error?: string;
  /** 字段级别的错误信息（如 {title: "作品书名不能为空"}） */
  errors?: Record<string, string>;
  /** 是否显示错误图标 */
  showIcon?: boolean;
  /** 自定义样式类名 */
  className?: string;
}

/**
 * 错误提示组件
 * 
 * 使用方式：
 * 1. 只显示API错误：<FormError error={apiError} />
 * 2. 只显示字段错误：<FormError errors={errors} />
 * 3. 同时显示：<FormError error={apiError} errors={errors} />
 */
export function FormError({
  error,
  errors,
  showIcon = true,
  className = '',
}: FormErrorProps) {
  // 如果没有错误，不渲染
  if (!error && !errors) {
    return null;
  }

  return (
    <div className={`${styles.container} ${className}`} role="alert">
      {showIcon && <span className={styles.icon}>⚠️</span>}
      
      <div className={styles.content}>
        {/* API级别错误 */}
        {error && (
          <div className={styles.apiError}>{error}</div>
        )}

        {/* 字段级别错误 */}
        {errors && Object.keys(errors).length > 0 && (
          <ul className={styles.fieldErrors}>
            {Object.entries(errors).map(([field, message]) => (
              <li key={field} className={styles.fieldError}>
                {message}
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}

/**
 * 字段级错误提示（用于单个输入框下方）
 * 
 * 使用方式：
 * <input ... />
 * <FieldError error={errors.title} />
 */
export function FieldError({ error }: { error?: string }) {
  if (!error) {
    return null;
  }

  return (
    <div className={styles.fieldErrorInline} role="alert">
      {error}
    </div>
  );
}

export default FormError;
