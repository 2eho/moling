'use client';

import styles from './ImportProgress.module.css';

/* ── Types ── */

export interface ProgressItem {
  id: string;
  label: string;
  icon: string;
  status: 'pending' | 'active' | 'done';
  result?: string;
}

export interface ImportProgressProps {
  phase: number;
  progressItems: ProgressItem[];
  overallProgress: number; // 0-100
  isVisible: boolean;
  title?: string;
  subtitle?: string;
}

/* ── Component ── */

export default function ImportProgress({
  phase,
  progressItems,
  overallProgress,
  isVisible,
  title = '全库分析 · 四库提取',
  subtitle = 'LLM 正在分析全部章节内容，提取人物库、时间线库、剧情承诺库和世界观库。',
}: ImportProgressProps) {
  const pct = Math.min(Math.round(overallProgress), 100);
  const doneCount = progressItems.filter((it) => it.status === 'done').length;

  return (
    <div className={`${styles.phaseContainer} ${isVisible ? styles.phaseVisible : ''}`}>
      <div className={styles.card}>
        <div className={styles.cardTitle}>
          <span className={styles.phaseBadge}>02</span>
          {title}
        </div>
        <div className={styles.cardSubtitle}>{subtitle}</div>

        {/* Progress Grid */}
        <div className={styles.progressGrid}>
          {progressItems.map((item) => (
            <div
              key={item.id}
              className={`${styles.progressItem} ${
                item.status === 'pending'
                  ? styles.progressItemPending
                  : item.status === 'active'
                  ? styles.progressItemActive
                  : styles.progressItemDone
              }`}
            >
              <div className={styles.progressIcon}>
                {item.status === 'done' ? (
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="var(--color-success)" strokeWidth="2.5" strokeLinecap="round">
                    <polyline points="20 6 9 17 4 12" />
                  </svg>
                ) : (
                  <span>{item.icon}</span>
                )}
              </div>
              <div className={styles.progressItemInfo}>
                <div className={styles.progressItemLabel}>{item.label}</div>
                <div className={styles.progressItemStatus}>
                  {item.status === 'done'
                    ? `✓ 提取完成${item.result ? `（${item.result}）` : ''}`
                    : item.status === 'active'
                    ? '正在提取...'
                    : '等待中...'}
                </div>
              </div>
              {item.status === 'active' && <div className={styles.progressSpinner} />}
            </div>
          ))}
        </div>

        {/* Overall Progress Bar */}
        <div className={styles.overallProgress}>
          <div className={styles.progressBarTrack}>
            <div
              className={styles.progressBarFill}
              style={{ width: `${pct}%` }}
            />
          </div>
          <div className={styles.progressStats}>
            <span>
              分析进度：<span className={styles.statValue}>{doneCount}/{progressItems.length}</span>
            </span>
            <span>
              <span className={styles.statValue}>{pct}%</span>
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
