"use client";

import { useState } from "react";
import { Input } from "@/components/ui/Input";
import { Button } from "@/components/ui/Button";
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
  const [error, setError] = useState("");

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
    setError("");

    if (!username.trim()) {
      setError("请输入用户名");
      return;
    }
    if (!email.trim()) {
      setError("请输入邮箱地址");
      return;
    }
    if (!password) {
      setError("请输入密码");
      return;
    }
    if (password !== confirmPassword) {
      setError("两次输入的密码不一致");
      return;
    }

    setLoading(true);
    try {
      await register(username, email, password);
      showToast("success", "注册成功，欢迎加入墨灵！");
    } catch (err) {
      setError(err instanceof Error ? err.message : "注册失败，请稍后重试");
    } finally {
      setLoading(false);
    }
  };

  return (
    <form className={styles.form} onSubmit={handleSubmit}>
      <Input
        label="用户名"
        type="text"
        placeholder="请输入用户名"
        value={username}
        onChange={(e) => setUsername(e.target.value)}
        icon="👤"
      />

      <Input
        label="邮箱"
        type="email"
        placeholder="请输入邮箱地址"
        value={email}
        onChange={(e) => setEmail(e.target.value)}
        icon="✉"
      />

      <div className={styles.passwordSection}>
        <Input
          label="密码"
          type="password"
          placeholder="请输入密码"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
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
      </div>

      <Input
        label="确认密码"
        type="password"
        placeholder="请再次输入密码"
        value={confirmPassword}
        onChange={(e) => setConfirmPassword(e.target.value)}
        icon="🔒"
      />

      {error && <p className={styles.error}>{error}</p>}

      <Button type="submit" variant="primary" size="lg" fullWidth loading={loading}>
        注册
      </Button>
    </form>
  );
}
