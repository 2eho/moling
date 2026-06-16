"use client";

import { useState } from "react";
import { Input } from "@/components/ui/Input";
import { Button } from "@/components/ui/Button";
import { FormError, FieldError } from "@/components/FormError";
import { validateForm, clearFieldError } from "@/lib/formValidation";
import { useAuth } from "@/hooks/useAuth";
import { showToast } from "@/components/ui/Toast";
import styles from "./RegisterForm.module.css";

export function RegisterForm() {
  const { register } = useAuth();
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [apiError, setApiError] = useState("");

  const validationRules = {
    username: [
      { required: true, message: '昵称不能为空' },
      { min: 2, message: '昵称至少2个字符' }
    ],
    email: [
      { required: true, message: '邮箱不能为空' },
      { pattern: /^[^\s@]+@[^\s@]+\.[^\s@]+$/, message: '邮箱格式不正确' }
    ],
    password: [
      { required: true, message: '密码不能为空' },
      { min: 8, message: '密码至少8个字符' }
    ]
  };

  const handleFieldChange = (field: string, value: string) => {
    setErrors(prev => clearFieldError(prev, field));
    setApiError("");
    
    switch (field) {
      case 'username': setUsername(value); break;
      case 'email': setEmail(value); break;
      case 'password': setPassword(value); break;
      case 'confirmPassword': setConfirmPassword(value); break;
    }
  };

  const getPasswordStrength = (pw: string): { label: string; level: number; color: string } => {
    let score = 0;
    if (pw.length >= 6) score += 1;
    if (pw.length >= 10) score += 1;
    if (/[A-Z]/.test(pw)) score += 1;
    if (/[0-9]/.test(pw)) score += 1;
    if (/[^A-Za-z0-9]/.test(pw)) score += 1;

    if (score <= 1) return { label: "弱", level: 1, color: "var(--color-error)" };
    if (score <= 3) return { label: "中", level: 2, color: "var(--color-warning)" };
    return { label: "强", level: 3, color: "var(--color-success)" };
  };

  const strength = password ? getPasswordStrength(password) : null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setApiError("");
    
    const formData = {
      username,
      email,
      password,
      confirmPassword
    };
    
    const validationErrors = validateForm(formData, validationRules);
    
    if (password !== confirmPassword) {
      validationErrors.confirmPassword = '两次输入的密码不一致';
    }
    
    if (Object.keys(validationErrors).length > 0) {
      setErrors(validationErrors);
      return;
    }
    
    setLoading(true);
    try {
      await register(username, email, password);
      showToast("success", "注册成功，欢迎加入墨灵！");
    } catch (err: any) {
      if (err?.status === 400 || err?.status === 422) {
        setErrors(err.errors || {});
      }
      setApiError(err instanceof Error ? err.message : '注册失败，请稍后重试');
    } finally {
      setLoading(false);
    }
  };

  return (
    <form className={styles.form} onSubmit={handleSubmit}>
      {apiError && <FormError error={apiError} />}
      
      <div className={styles.field}>
        <Input
          label="用户名 *"
          type="text"
          placeholder="请输入用户名"
          value={username}
          onChange={(e) => handleFieldChange('username', e.target.value)}
          error={errors.username}
          icon="👤"
        />
        <FieldError error={errors.username} />
      </div>

      <div className={styles.field}>
        <Input
          label="邮箱 *"
          type="email"
          placeholder="请输入邮箱地址"
          value={email}
          onChange={(e) => handleFieldChange('email', e.target.value)}
          error={errors.email}
          icon="✉"
        />
        <FieldError error={errors.email} />
      </div>

      <div className={styles.passwordSection}>
        <Input
          label="密码 *"
          type="password"
          placeholder="请输入密码（至少8个字符）"
          value={password}
          onChange={(e) => handleFieldChange('password', e.target.value)}
          error={errors.password}
          icon="🔒"
        />
        {strength && (
          <div className={styles.strengthIndicator}>
            <div className={styles.strengthBar}>
              {[1, 2, 3].map((level) => (
                <div
                  key={level}
                  className={`${styles.strengthSegment} ${
                    level <= strength.level ? styles.active : ""
                  }`}
                  style={{
                    backgroundColor: level <= strength.level ? strength.color : undefined,
                  }}
                />
              ))}
            </div>
            <span className={styles.strengthLabel} style={{ color: strength.color }}>
              密码强度：{strength.label}
            </span>
          </div>
        )}
        <FieldError error={errors.password} />
      </div>

      <div className={styles.field}>
        <Input
          label="确认密码 *"
          type="password"
          placeholder="请再次输入密码"
          value={confirmPassword}
          onChange={(e) => handleFieldChange('confirmPassword', e.target.value)}
          error={errors.confirmPassword}
          icon="🔒"
        />
        <FieldError error={errors.confirmPassword} />
      </div>

      <FormError errors={errors} />
      
      <Button type="submit" variant="primary" size="lg" fullWidth loading={loading}>
        注册
      </Button>
    </form>
  );
}
