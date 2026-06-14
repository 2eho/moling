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
    <div className={styles.page}>
      <div className={styles.container}>
        <div className={styles.card}>
          <div className={styles.header}>
            <div className={styles.logo}>
              <span className={styles.logoIndigo}>墨</span>灵
            </div>
            <p className={styles.subtitle}>AI 驱动的网文创作平台</p>
          </div>

          <AuthTabs activeTab={activeTab} onChange={setActiveTab} />

          {activeTab === "login" && <LoginForm onSwitchToReset={() => setActiveTab("reset")} />}
          {activeTab === "register" && <RegisterForm />}
          {activeTab === "reset" && <ResetPasswordForm />}
        </div>
      </div>
    </div>
  );
}
