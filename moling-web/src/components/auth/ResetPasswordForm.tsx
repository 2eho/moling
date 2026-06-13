"use client";

import { useState } from "react";
import { Input } from "@/components/ui/Input";
import { Button } from "@/components/ui/Button";
import { useAuth } from "@/hooks/useAuth";
import { showToast } from "@/components/ui/Toast";
import styles from "./ResetPasswordForm.module.css";

export function ResetPasswordForm() {
  const { resetPassword } = useAuth();
  const [email, setEmail] = useState("");
  const [loading, setLoading] = useState(false);
  const [sent, setSent] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");

    if (!email.trim()) {
      setError("请输入邮箱地址");
      return;
    }

    setLoading(true);
    try {
      await resetPassword(email);
      setSent(true);
      showToast("success", "重置链接已发送到您的邮箱");
    } catch (err) {
      setError(err instanceof Error ? err.message : "发送失败，请稍后重试");
    } finally {
      setLoading(false);
    }
  };

  if (sent) {
    return (
      <div className={styles.sentContainer}>
        <span className={styles.sentIcon}>✓</span>
        <h4 className={styles.sentTitle}>邮件已发送</h4>
        <p className={styles.sentText}>
          密码重置链接已发送至 <strong>{email}</strong>，请查收邮件并按提示操作。
        </p>
      </div>
    );
  }

  return (
    <form className={styles.form} onSubmit={handleSubmit}>
      <p className={styles.description}>
        输入您注册时使用的邮箱地址，我们将向您发送密码重置链接。
      </p>

      <Input
        label="邮箱"
        type="email"
        placeholder="请输入注册邮箱"
        value={email}
        onChange={(e) => setEmail(e.target.value)}
        icon="✉"
      />

      {error && <p className={styles.error}>{error}</p>}

      <Button type="submit" variant="primary" size="lg" fullWidth loading={loading}>
        发送重置链接
      </Button>
    </form>
  );
}
