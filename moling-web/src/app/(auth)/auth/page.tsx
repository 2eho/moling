"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { AuthTabs } from "@/components/auth/AuthTabs";
import { LoginForm } from "@/components/auth/LoginForm";
import { RegisterForm } from "@/components/auth/RegisterForm";
import { ResetPasswordForm } from "@/components/auth/ResetPasswordForm";
import { useAuth } from "@/contexts/AuthContext";
import styles from "./auth.module.css";

export default function AuthPage() {
  const [activeTab, setActiveTab] = useState("login");
  const { isAuthenticated, isLoading } = useAuth();
  const router = useRouter();

  // 如果已登录，重定向到项目页
  useEffect(() => {
    if (!isLoading && isAuthenticated) {
      const lastProjectId = localStorage.getItem("lastProjectId");
      if (lastProjectId) {
        router.push(`/workspace/${lastProjectId}`);
      } else {
        router.push("/projects");
      }
    }
  }, [isLoading, isAuthenticated, router]);

  // 如果正在加载或已登录，不显示内容
  if (isLoading || isAuthenticated) {
    return null;
  }

  return (
    <div className={styles.card}>
      <div className={styles.header}>
        <span className={styles.logo}>✒</span>
        <h1 className={styles.title}>墨灵</h1>
        <p className={styles.subtitle}>AI 驱动的创意写作平台</p>
      </div>

      <AuthTabs activeTab={activeTab} onChange={setActiveTab} />

      {activeTab === "login" && <LoginForm onSwitchToReset={() => setActiveTab("reset")} />}
      {activeTab === "register" && <RegisterForm />}
      {activeTab === "reset" && <ResetPasswordForm />}
    </div>
  );
}
