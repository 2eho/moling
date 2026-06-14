'use client';

import { useState, useEffect } from 'react';
import styles from './History.module.css';

export default function HistoryPage() {
  const [history, setHistory] = useState<Array<{
    id: string;
    chapterId: string;
    chapterTitle: string;
    taskId: string;
    status: string;
    wordCount: number;
    timeSpent: number;
    createdAt: string;
  }>>([]);
  const [loading, setLoading] = useState(true);
  const [selectedRecord, setSelectedRecord] = useState<null | typeof history[0]>(null);

  // 模拟数据
  useEffect(() => {
    setLoading(true);
    // Mock data
    setTimeout(() => {
      setHistory([
        {
          id: '1',
          chapterId: 'ch-15',
          chapterTitle: '第15章·宗门考核',
          taskId: 'task-001',
          status: 'completed',
          wordCount: 3200,
          timeSpent: 13.2,
          createdAt: '2026-06-14T10:30:00Z',
        },
        {
          id: '2',
          chapterId: 'ch-14',
          chapterTitle: '第14章·暗夜密谈',
          taskId: 'task-002',
          status: 'completed',
          wordCount: 2800,
          timeSpent: 11.5,
          createdAt: '2026-06-13T22:15:00Z',
        },
        {
          id: '3',
          chapterId: 'ch-13',
          chapterTitle: '第13章·后山禁地',
          taskId: 'task-003',
          status: 'failed',
          wordCount: 0,
          timeSpent: 0,
          createdAt: '2026-06-12T18:45:00Z',
        },
      ]);
      setLoading(false);
    }, 1000);
  }, []);

  const handleViewDetail = (record: typeof history[0]) => {
    setSelectedRecord(record);
  };

  const handleRegenerate = (record: typeof history[0]) => {
    alert(`重新生成章节 ${record.chapterTitle}...（演示）`);
  };

  const getStatusText = (status: string) => {
    switch (status) {
      case 'pending': return '等待中';
      case 'preprocessing': return '预处理中';
      case 'generating': return '生成中';
      case 'validating': return '校验中';
      case 'completed': return '已完成';
      case 'failed': return '失败';
      default: return status;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed': return '#34d399';
      case 'failed': return '#ef4444';
      default: return '#9ca3c4';
    }
  };

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <h1 className={styles.title}>生成历史</h1>
        <p className={styles.subtitle}>查看所有生成记录</p>
      </div>

      <div className={styles.content}>
        {loading ? (
          <div className={styles.loading}>加载中...</div>
        ) : history.length === 0 ? (
          <div className={styles.empty}>暂无生成记录</div>
        ) : (
          <div className={styles.list}>
            {history.map(record => (
              <div key={record.id} className={styles.recordCard}>
                <div className={styles.recordHeader}>
                  <div className={styles.recordTitle}>{record.chapterTitle}</div>
                  <div
                    className={styles.recordStatus}
                    style={{ color: getStatusColor(record.status) }}
                  >
                    {getStatusText(record.status)}
                  </div>
                </div>

                <div className={styles.recordMeta}>
                  <span>📏 {record.wordCount} 字</span>
                  <span>⏱️ {record.timeSpent}s</span>
                  <span>📅 {new Date(record.createdAt).toLocaleString('zh-CN')}</span>
                </div>

                <div className={styles.recordActions}>
                  <button
                    className={styles.viewBtn}
                    onClick={() => handleViewDetail(record)}
                  >
                    查看详情
                  </button>
                  {record.status === 'completed' && (
                    <button
                      className={styles.regenerateBtn}
                      onClick={() => handleRegenerate(record)}
                    >
                      重新生成
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}

        {/* 详情弹窗 */}
        {selectedRecord && (
          <div className={styles.modalOverlay} onClick={(e) => e.target === e.currentTarget && setSelectedRecord(null)}>
            <div className={styles.modal}>
              <div className={styles.modalHeader}>
                <h3>生成详情</h3>
                <button
                  className={styles.modalClose}
                  onClick={() => setSelectedRecord(null)}
                >
                  ✕
                </button>
              </div>
              <div className={styles.modalBody}>
                <div className={styles.detailRow}>
                  <span>章节：</span>
                  <span>{selectedRecord.chapterTitle}</span>
                </div>
                <div className={styles.detailRow}>
                  <span>状态：</span>
                  <span style={{ color: getStatusColor(selectedRecord.status) }}>
                    {getStatusText(selectedRecord.status)}
                  </span>
                </div>
                <div className={styles.detailRow}>
                  <span>字数：</span>
                  <span>{selectedRecord.wordCount} 字</span>
                </div>
                <div className={styles.detailRow}>
                  <span>耗时：</span>
                  <span>{selectedRecord.timeSpent}s</span>
                </div>
                <div className={styles.detailRow}>
                  <span>时间：</span>
                  <span>{new Date(selectedRecord.createdAt).toLocaleString('zh-CN')}</span>
                </div>
                <div className={styles.detailRow}>
                  <span>任务 ID：</span>
                  <span>{selectedRecord.taskId}</span>
                </div>
              </div>
              <div className={styles.modalFooter}>
                <button
                  className={styles.closeBtn}
                  onClick={() => setSelectedRecord(null)}
                >
                  关闭
                </button>
                {selectedRecord.status === 'completed' && (
                  <button
                    className={styles.regenerateBtn}
                    onClick={() => {
                      handleRegenerate(selectedRecord);
                      setSelectedRecord(null);
                    }}
                  >
                    重新生成
                  </button>
                )}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
