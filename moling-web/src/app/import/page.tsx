'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import styles from './Import.module.css';

/* ── Component ── */

export default function ImportPage() {
  const router = useRouter();
  const [countdown, setCountdown] = useState(3);

  useEffect(() => {
    if (countdown <= 0) {
      router.push('/projects');
      return;
    }

    const timer = setTimeout(() => {
      setCountdown((prev) => prev - 1);
    }, 1000);

    return () => clearTimeout(timer);
  }, [countdown, router]);

  return (
    <div className={styles.redirectContainer}>
      <div className={styles.redirectCard}>
        <div className={styles.redirectIcon}>
          <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="var(--color-brand-indigo)" strokeWidth="1.5" strokeLinecap="round">
            <path d="M13 2L3 14h9l-1 8 10-12h-9l 1-8z" />
          </svg>
        </div>
        <h1 className={styles.redirectTitle}>导入功能已迁移</h1>
        <p className={styles.redirectSubtitle}>
          导入功能已整合到项目页面中。
          <br />
          即将在 {countdown} 秒后跳转到项目列表...
        </p>
        <button
          className={styles.redirectButton}
          onClick={() => router.push('/projects')}
        >
          立即跳转到项目列表
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <polyline points="9 18 15 12 9 6" />
          </svg>
        </button>
      </div>
    </div>
  );
}
