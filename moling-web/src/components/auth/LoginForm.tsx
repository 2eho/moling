"use client";

import { useState } from "react";
import { Input } from "@/components/ui/Input";
import { Button } from "@/components/ui/Button";
import { useAuth } from "@/hooks/useAuth";
import { showToast } from "@/components/ui/Toast";
import styles from "./LoginForm.module.css";

interface LoginFormProps {
  onSwitchToReset: () => void;
}

export function LoginForm({ onSwitchToReset }: LoginFormProps) {
  const { login } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");

    if (!email.trim()) {
      setError("请输入邮箱地址");
      return;
    }
    if (!password) {
      setError("请输入密码");
      return;
    }

    setLoading(true);
    try {
      await login(email, password);
      showToast("success", "登录成功，欢迎回来！");
    } catch (err) {
      setError(err instanceof Error ? err.message : "登录失败，请稍后重试");
    } finally {
      setLoading(false);
    }
  };

  return (
    <form className={styles.form} onSubmit={handleSubmit}>
      <Input
        label="邮箱 *"
        type="email"
        placeholder="请输入邮箱地址"
        value={email}
        onChange={(e) => setEmail(e.target.value)}
        icon="✉"
        error={error && !email.trim() ? error : undefined}
      />

      <Input
        label="密码 *"
        type="password"
        placeholder="请输入密码"
        value={password}
        onChange={(e) => setPassword(e.target.value)}
        icon="🔒"
        error={error && !password ? error : undefined}
      />

      {error && <p className={styles.error}>{error}</p>}

      <Button type="submit" variant="primary" size="lg" fullWidth loading={loading}>
        登录
      </Button>

      <button
        type="button"
        className={styles.forgotLink}
        onClick={onSwitchToReset}
      >
        忘记密码？
      </button>
    </form>
  );
}
