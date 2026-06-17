"use client";

import { useParams } from "next/navigation";
import { HealthDashboard } from "@/components/health/HealthDashboard";
import styles from "./health.module.css";

export default function HealthPage() {
  const params = useParams();
  const projectId = params.projectId as string;

  return (
    <div className={styles.page}>
      <div className={styles.pageHeader}>
        <h1 className={styles.pageTitle}>健康监控仪表盘</h1>
        <p className={styles.pageDescription}>
          查看项目中所有子情节的健康状态，包括 R1（严重）、R2（警告）和 R3（信息）级别的告警
        </p>
      </div>
      <div className={styles.dashboardWrapper}>
        <HealthDashboard projectId={projectId} />
      </div>
    </div>
  );
}
