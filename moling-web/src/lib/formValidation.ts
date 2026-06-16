/**
 * 统一表单验证工具库
 * 
 * 提供可复用的表单验证功能，确保：
 * 1. 所有必填字段都有验证
 * 2. 错误提示具体、明确
 * 3. 支持前端验证和后端验证错误显示
 */

export interface ValidationRule {
  /** 是否必填 */
  required?: boolean;
  /** 最小长度（字符串）或最小值（数字） */
  min?: number;
  /** 最大长度（字符串）或最大值（数字） */
  max?: number;
  /** 正则表达式匹配 */
  pattern?: RegExp;
  /** 自定义验证函数 */
  validate?: (value: unknown) => boolean;
  /** 错误提示信息 */
  message: string;
}

export interface ValidationRules {
  [field: string]: ValidationRule[];
}

export interface FormErrors {
  [field: string]: string;
}

export interface FormData {
  [field: string]: unknown;
}

/**
 * 验证表单数据
 * @param data 表单数据
 * @param rules 验证规则
 * @returns 错误对象（字段名 -> 错误信息）
 */
export function validateForm(data: FormData, rules: ValidationRules): FormErrors {
  const errors: FormErrors = {};

  for (const [field, fieldRules] of Object.entries(rules)) {
    const value = data[field];
    
    for (const rule of fieldRules) {
      // 必填验证
      if (rule.required) {
        if (value === undefined || value === null || value === '') {
          errors[field] = rule.message;
          break; // 找到一个错误就停止验证该字段
        }
      }

      // 如果字段为空且非必填，跳过其他验证
      if (value === undefined || value === null || value === '') {
        continue;
      }

      // 最小长度/值验证
      if (rule.min !== undefined) {
        if (typeof value === 'string' && value.length < rule.min) {
          errors[field] = rule.message;
          break;
        }
        if (typeof value === 'number' && value < rule.min) {
          errors[field] = rule.message;
          break;
        }
      }

      // 最大长度/值验证
      if (rule.max !== undefined) {
        if (typeof value === 'string' && value.length > rule.max) {
          errors[field] = rule.message;
          break;
        }
        if (typeof value === 'number' && value > rule.max) {
          errors[field] = rule.message;
          break;
        }
      }

      // 正则表达式验证
      if (rule.pattern && typeof value === 'string') {
        if (!rule.pattern.test(value)) {
          errors[field] = rule.message;
          break;
        }
      }

      // 自定义验证函数
      if (rule.validate) {
        if (!rule.validate(value)) {
          errors[field] = rule.message;
          break;
        }
      }
    }
  }

  return errors;
}

/**
 * 解析API错误响应
 * @param error 错误对象（来自apiClient）
 * @returns 格式化的错误信息
 */
export function parseApiError(error: {
  status?: number;
  message?: string;
  data?: {
    message?: string;
    detail?: string;
    errors?: Record<string, string>;
    validation_errors?: Record<string, string>;
  };
}): { message: string; errors?: Record<string, string> } {
  // 网络错误
  if (!error.status) {
    return { message: '网络连接失败，请检查网络后重试' };
  }

  // 服务器错误
  if (error.status >= 500) {
    return { message: '服务器内部错误，请稍后重试' };
  }

  // 客户端错误（400, 422等）
  if (error.status === 400 || error.status === 422) {
    const data = error.data;
    
    // 尝试提取验证错误
    if (data?.errors) {
      return {
        message: '请检查表单输入',
        errors: data.errors
      };
    }
    
    if (data?.validation_errors) {
      return {
        message: '请检查表单输入',
        errors: data.validation_errors
      };
    }

    // 提取错误消息
    const message = data?.message || data?.detail || error.message || '请求错误';
    return { message };
  }

  // 认证错误
  if (error.status === 401) {
    return { message: '未授权，请重新登录' };
  }

  // 权限错误
  if (error.status === 403) {
    return { message: '没有权限执行此操作' };
  }

  // 默认错误
  return {
    message: error.message || `错误 (${error.status})`
  };
}

/**
 * 检查表单是否有错误
 * @param errors 错误对象
 * @returns 是否有错误
 */
export function hasErrors(errors: FormErrors): boolean {
  return Object.keys(errors).length > 0;
}

/**
 * 清除字段错误（用户开始输入时调用）
 * @param errors 当前错误对象
 * @param field 字段名
 * @returns 新的错误对象
 */
export function clearFieldError(errors: FormErrors, field: string): FormErrors {
  const newErrors = { ...errors };
  delete newErrors[field];
  return newErrors;
}
