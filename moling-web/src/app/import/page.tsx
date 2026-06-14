'use client';

import { useState, useEffect, useRef } from 'react';
import styles from './Import.module.css';
import { importApi } from '@/lib/api';
import type { ImportProgress } from '@/api';

export default function ImportPage() {
  const [projectId, setProjectId] = useState('current-project-id');
  const [uploading, setUploading] = useState(false);
  const [taskId, setTaskId] = useState<string | null>(null);
  const [progress, setProgress] = useState<ImportProgress | null>(null);
  const [result, setResult] = useState<ImportProgress['result'] | null>(null);
  const [history, setHistory] = useState<Array<{
    id: string;
    fileName: string;
    status: string;
    createdAt: string;
  }>>([]);
  const [error, setError] = useState<string | null>(null);
  const [options, setOptions] = useState({
    analyzeCharacters: true,
    analyzeTimeline: true,
    analyzeCommitments: true,
    analyzeWorldview: true,
  });

  const fileInputRef = useRef<HTMLInputElement>(null);

  // 加载导入历史
  useEffect(() => {
    const loadHistory = async () => {
      try {
        const data = await importApi.getImportHistory(projectId);
        setHistory(data);
      } catch (error) {
        console.error('加载导入历史失败:', error);
      }
    };

    loadHistory();
  }, [projectId]);

  // 轮询进度
  useEffect(() => {
    if (!taskId) return;

    const pollProgress = async () => {
      try {
        const data = await importApi.getImportProgress(taskId);
        setProgress(data as any);

        if (data.status === 'completed' && data.result) {
          setResult(data.result);
          setUploading(false);
          // 刷新历史
          const historyData = await importApi.getImportHistory(projectId);
          setHistory(historyData);
          return;
        }

        if (data.status === 'failed') {
          setError(data.error || '导入失败');
          setUploading(false);
          return;
        }

        // 继续轮询
        setTimeout(pollProgress, 2000);
      } catch (error) {
        console.error('获取进度失败:', error);
      }
    };

    pollProgress();
  }, [taskId, projectId]);

  // 处理文件上传
  const handleFileUpload = async (file: File) => {
    setUploading(true);
    setError(null);
    setProgress(null);
    setResult(null);

    try {
      const response = await importApi.uploadAndImport(projectId, file, options);
      setTaskId(response.taskId);
    } catch (error) {
      console.error('上传失败:', error);
      setError(error instanceof Error ? error.message : '上传失败');
      setUploading(false);
    }
  };

  // 拖拽上传
  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    const file = e.dataTransfer.files[0];
    if (file) handleFileUpload(file);
  };

  const handleDragOver = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
  };

  // 点击上传
  const handleClickUpload = () => {
    fileInputRef.current?.click();
  };

  const handleFileInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) handleFileUpload(file);
  };

  const getPhaseText = (phase?: string) => {
    switch (phase) {
      case 'parsing': return '解析文件中...';
      case 'analyzing': return '分析中...';
      case 'saving': return '保存结果中...';
      default: return '准备中...';
    }
  };

  const getStatusText = (status: string) => {
    switch (status) {
      case 'pending': return '等待中';
      case 'parsing': return '解析中';
      case 'analyzing': return '分析中';
      case 'saving': return '保存中';
      case 'completed': return '已完成';
      case 'failed': return '失败';
      default: return status;
    }
  };

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <h1 className={styles.title}>导入</h1>
      </div>

      <div className={styles.content}>
        {/* 上传区域 */}
        <div
          className={styles.uploadArea}
          onDrop={handleDrop}
          onDragOver={handleDragOver}
          onClick={handleClickUpload}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept=".txt,.doc,.docx,.pdf,.epub"
            style={{ display: 'none' }}
            onChange={handleFileInputChange}
          />

          {uploading ? (
            <div className={styles.uploading}>
              <div className={styles.uploadIcon}>⏳</div>
              <div>正在上传...</div>
            </div>
          ) : (
            <div className={styles.uploadPrompt}>
              <div className={styles.uploadIcon}>📂</div>
              <div className={styles.uploadText}>拖拽文件到这里，或点击上传</div>
              <div className={styles.uploadHint}>
                支持 .txt, .doc, .docx, .pdf, .epub 格式
              </div>
            </div>
          )}
        </div>

        {/* 选项 */}
        <div className={styles.options}>
          <label className={styles.checkbox}>
            <input
              type="checkbox"
              checked={options.analyzeCharacters}
              onChange={(e) =>
                setOptions({ ...options, analyzeCharacters: e.target.checked })
              }
            />
            <span>分析角色</span>
          </label>
          <label className={styles.checkbox}>
            <input
              type="checkbox"
              checked={options.analyzeTimeline}
              onChange={(e) =>
                setOptions({ ...options, analyzeTimeline: e.target.checked })
              }
            />
            <span>分析时间线</span>
          </label>
          <label className={styles.checkbox}>
            <input
              type="checkbox"
              checked={options.analyzeCommitments}
              onChange={(e) =>
                setOptions({ ...options, analyzeCommitments: e.target.checked })
              }
            />
            <span>分析剧情承诺</span>
          </label>
          <label className={styles.checkbox}>
            <input
              type="checkbox"
              checked={options.analyzeWorldview}
              onChange={(e) =>
                setOptions({ ...options, analyzeWorldview: e.target.checked })
              }
            />
            <span>分析世界观</span>
          </label>
        </div>

        {/* 进度展示 */}
        {progress && (
          <div className={styles.progressCard}>
            <h2 className={styles.progressTitle}>⏳ 导入进度</h2>
            <div className={styles.progressStatus}>
              {getPhaseText(progress.currentPhase)}
            </div>
            <div className={styles.progressBar}>
              <div
                className={styles.progressFill}
                style={{ width: `${progress.progress}%` }}
              />
            </div>
            <div className={styles.progressPercent}>{progress.progress}%</div>

            {/* 阶段展示 */}
            <div className={styles.phases}>
              {['parsing', 'analyzing', 'saving'].map((phase) => (
                <div
                  key={phase}
                  className={`${styles.phase} ${
                    progress.currentPhase === phase ? styles.phaseActive : ''
                  } ${progress.status === 'completed' ? styles.phaseCompleted : ''}`}
                >
                  {phase === 'parsing' && '📄 解析'}
                  {phase === 'analyzing' && '🔍 分析'}
                  {phase === 'saving' && '💾 保存'}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* 错误展示 */}
        {error && (
          <div className={styles.errorCard}>
            <div className={styles.errorIcon}>❌</div>
            <div className={styles.errorText}>{error}</div>
          </div>
        )}

        {/* 结果展示 */}
        {result && (
          <div className={styles.resultCard}>
            <h2 className={styles.resultTitle}>✅ 导入完成</h2>
            <div className={styles.resultStats}>
              <div className={styles.resultStat}>
                <span className={styles.resultStatLabel}>角色：</span>
                <span className={styles.resultStatValue}>{result.charactersCreated} 个</span>
              </div>
              <div className={styles.resultStat}>
                <span className={styles.resultStatLabel}>时间线事件：</span>
                <span className={styles.resultStatValue}>{result.eventsCreated} 个</span>
              </div>
              <div className={styles.resultStat}>
                <span className={styles.resultStatLabel}>剧情承诺：</span>
                <span className={styles.resultStatValue}>{result.commitmentsCreated} 个</span>
              </div>
              <div className={styles.resultStat}>
                <span className={styles.resultStatLabel}>世界观条目：</span>
                <span className={styles.resultStatValue}>{result.entriesCreated} 个</span>
              </div>
            </div>
          </div>
        )}

        {/* 导入历史 */}
        <div className={styles.history}>
          <h2 className={styles.historyTitle}>📋 导入历史</h2>
          {history.length === 0 ? (
            <div className={styles.historyEmpty}>暂无导入历史</div>
          ) : (
            <div className={styles.historyList}>
              {history.map((item) => (
                <div key={item.id} className={styles.historyItem}>
                  <div className={styles.historyFileName}>{item.fileName}</div>
                  <div className={styles.historyStatus}>
                    状态：{getStatusText(item.status)}
                  </div>
                  <div className={styles.historyDate}>
                    {new Date(item.createdAt).toLocaleDateString('zh-CN')}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
