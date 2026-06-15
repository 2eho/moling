'use client';

import { useState, useEffect, useRef, useCallback } from 'react';
import styles from './Import.module.css';
import { importApi } from '@/lib/api';
import type { ImportProgress } from '@/api';

const PROJECT_NAME = '星穹之下';
const TOTAL_CHAPTERS = 23;

interface StepData {
  label: string;
  active: boolean;
  done: boolean;
}

interface AnalysisItem {
  key: string;
  label: string;
  status: 'pending' | 'active' | 'done';
}

interface DynamicChapter {
  number: string;
  title: string;
  events: string[];
}

interface DynamicInsight {
  icon: string;
  label: string;
  getValue: () => string;
}

export default function ImportPage() {
  const [projectId] = useState('current-project-id');
  const [currentStep, setCurrentStep] = useState(0);
  const [importMethod, setImportMethod] = useState<'paste' | 'file'>('paste');
  const [pasteText, setPasteText] = useState('');
  const [fileName, setFileName] = useState<string | null>(null);
  const [fileSize, setFileSize] = useState<string | null>(null);
  const [isDragOver, setIsDragOver] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [analysisItems, setAnalysisItems] = useState<AnalysisItem[]>([
    { key: 'characters', label: '人物库提取', status: 'pending' },
    { key: 'timeline', label: '时间线库提取', status: 'pending' },
    { key: 'commitments', label: '剧情承诺库提取', status: 'pending' },
    { key: 'worldview', label: '世界观库提取', status: 'pending' },
  ]);
  const [progress, setProgress] = useState(0);
  const [progressPercent, setProgressPercent] = useState(0);
  const [hasConflicts, setHasConflicts] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [taskId, setTaskId] = useState<string | null>(null);
  const [importProgress, setImportProgress] = useState<ImportProgress | null>(null);
  const [result, setResult] = useState<ImportProgress['result'] | null>(null);
  const [history, setHistory] = useState<Array<{
    id: string;
    fileName: string;
    status: string;
    createdAt: string;
  }>>([]);
  const [error, setError] = useState<string | null>(null);
  const [options] = useState({
    analyzeCharacters: true,
    analyzeTimeline: true,
    analyzeCommitments: true,
    analyzeWorldview: true,
  });

  const fileInputRef = useRef<HTMLInputElement>(null);

  // Load import history
  useEffect(() => {
    const loadHistory = async () => {
      try {
        const data = await importApi.getImportHistory(projectId);
        setHistory(data.map((item: { id: string; file_name: string; status: string; created_at: string }) => ({
          id: item.id,
          fileName: item.file_name,
          status: item.status,
          createdAt: item.created_at,
        })));
      } catch (error) {
        console.error('加载导入历史失败:', error);
      }
    };
    loadHistory();
  }, [projectId]);

  // Poll import progress
  useEffect(() => {
    if (!taskId) return;

    const pollProgress = async () => {
      try {
        const res = await importApi.getJobStatus(projectId, taskId);
        const jobStatus = res.data;
        setImportProgress(jobStatus as any);

        if (jobStatus.status === 'completed' && jobStatus.result) {
          setResult({
            charactersCreated: jobStatus.result.characters_created,
            eventsCreated: jobStatus.result.events_created,
            commitmentsCreated: jobStatus.result.commitments_created,
            entriesCreated: jobStatus.result.entries_created,
          });
          setUploading(false);
          const historyData = await importApi.getImportHistory(projectId);
          setHistory(historyData.map((item: { id: string; file_name: string; status: string; created_at: string }) => ({
            id: item.id,
            fileName: item.file_name,
            status: item.status,
            createdAt: item.created_at,
          })));
          setCurrentStep(4);
          return;
        }

        if (jobStatus.status === 'failed') {
          setError(jobStatus.error || '导入失败');
          setUploading(false);
          return;
        }

        setTimeout(pollProgress, 2000);
      } catch (error) {
        console.error('获取进度失败:', error);
      }
    };

    pollProgress();
  }, [taskId, projectId]);

  const getWordCount = useCallback((text: string): number => {
    return text.replace(/\s/g, '').length;
  }, []);

  const handleFileUpload = async (file: File) => {
    setUploading(true);
    setError(null);
    setImportProgress(null);
    setResult(null);

    try {
      const response = await importApi.uploadAndImport(projectId, file, {
        analyze_characters: options.analyzeCharacters,
        analyze_timeline: options.analyzeTimeline,
        analyze_commitments: options.analyzeCommitments,
        analyze_worldview: options.analyzeWorldview,
      });
      setTaskId(response.job_id);
      setFileName(file.name);
      setFileSize(`${(file.size / 1024).toFixed(0)} KB`);
    } catch (err) {
      console.error('上传失败:', err);
      setError(err instanceof Error ? err.message : '上传失败');
      setUploading(false);
    }
  };

  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragOver(false);
    const file = e.dataTransfer.files[0];
    if (file) handleFileUpload(file);
  };

  const handleDragOver = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragOver(true);
  };

  const handleDragLeave = () => {
    setIsDragOver(false);
  };

  const handleClickUpload = () => {
    fileInputRef.current?.click();
  };

  const handleFileInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) handleFileUpload(file);
  };

  const runAnalysis = useCallback(async () => {
    setCurrentStep(1);
    setIsProcessing(true);

    const order = ['characters', 'timeline', 'commitments', 'worldview'];

    for (let i = 0; i < order.length; i++) {
      setAnalysisItems(prev =>
        prev.map(item =>
          item.key === order[i] ? { ...item, status: 'active' as const } : item
        )
      );

      await new Promise(resolve => setTimeout(resolve, 800));

      setAnalysisItems(prev =>
        prev.map(item =>
          item.key === order[i] ? { ...item, status: 'done' as const } : item
        )
      );

      setProgress(i + 1);
      setProgressPercent(Math.round(((i + 1) / order.length) * 100));
    }

    // Move to phase 2
    setCurrentStep(2);

    await new Promise(resolve => setTimeout(resolve, 1200));

    // Move to phase 3
    setCurrentStep(3);
    setIsProcessing(false);
  }, []);

  const handleConfirmImport = async () => {
    if (isProcessing) return;
    setIsProcessing(true);

    // Simulate import
    await new Promise(resolve => setTimeout(resolve, 600));
    setCurrentStep(4);
    setIsProcessing(false);
  };

  const handleAbort = () => {
    setCurrentStep(0);
    setAnalysisItems([
      { key: 'characters', label: '人物库提取', status: 'pending' },
      { key: 'timeline', label: '时间线库提取', status: 'pending' },
      { key: 'commitments', label: '剧情承诺库提取', status: 'pending' },
      { key: 'worldview', label: '世界观库提取', status: 'pending' },
    ]);
    setProgress(0);
    setProgressPercent(0);
  };

  const steps: StepData[] = [
    { label: '导入方式', active: currentStep === 0, done: currentStep > 0 },
    { label: '全库分析', active: currentStep === 1, done: currentStep > 1 },
    { label: '动态层', active: currentStep === 2, done: currentStep > 2 },
    { label: '审查确认', active: currentStep === 3, done: currentStep > 3 },
  ];

  const dynamicChapters: DynamicChapter[] = [
    {
      number: '第 21 章',
      title: '秘境入口',
      events: ['苏铭发现玄天宗秘境入口', '与叶青寒对峙，得到禁术残卷线索', '夜无痕暗中跟随'],
    },
    {
      number: '第 22 章',
      title: '禁地交锋',
      events: ['苏铭在秘境中遭遇守护兽', '叶青寒出手相助，伤势恶化', '发现王城地下有异响'],
    },
    {
      number: '第 23 章',
      title: '七国密约浮现',
      events: ['苏铭解封部分禁术残卷', '神秘人现身，警告七国势力已渗入', '玄天宗掌门召集紧急会议'],
    },
  ];

  const libIcons: Record<string, string> = {
    characters: '👥',
    timeline: '⏱️',
    commitments: '📖',
    worldview: '🌍',
  };

  const libResults: Record<string, string> = {
    characters: '12 人',
    timeline: '5 个节点',
    commitments: '8 项',
    worldview: '6 项',
  };

  const conflicts = [
    { main: '人物「叶青寒」在第 15 章受伤，但第 18 章参与战斗', detail: '时间线矛盾：叶青寒伤势较重，按设定第 16-17 章应在养伤，第 18 章突然出现在战场未被解释。' },
    { main: '王城地下异响在第 10 章埋设后未在第 20-23 章回收', detail: '剧情承诺未收束：该悬念间隔 10 章未提及，建议在后续章节中适时回收。' },
  ];

  // ── Desktop View ──
  const desktopView = (
    <div className={styles.desktopShell}>
      <header className={styles.header}>
        <button className={styles.headerBackBtn} onClick={() => { if (confirm('返回后将丢失当前进度，确定返回吗？')) window.history.back(); }} title="返回我的作品">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
            <polyline points="15 18 9 12 15 6" />
          </svg>
        </button>
        <span className={styles.headerTitle}>导入已有小说</span>
        <div className={styles.headerSpacer}></div>
        <div className={styles.headerProject}>
          <span className={styles.projectDot}></span>
          <span className={styles.projectName}>{PROJECT_NAME}</span>
          <span style={{ fontSize: '11px', color: 'var(--color-text-disabled)' }}>{TOTAL_CHAPTERS}章</span>
        </div>
      </header>

      <div className={styles.mainScroll}>
        {/* Step Indicator */}
        <div className={styles.stepIndicator}>
          {steps.map((step, i) => (
            <span key={i} style={{ display: 'contents' }}>
              <div className={`${styles.stepNode} ${step.active ? styles.stepNodeActive : ''} ${step.done ? styles.stepNodeDone : ''}`}>
                <div className={styles.stepCircle}>{i + 1}</div>
                <span className={styles.stepLabel}>{step.label}</span>
              </div>
              {i < steps.length - 1 && (
                <div className={`${styles.stepConnector} ${step.done ? styles.stepConnectorDone : ''}`}></div>
              )}
            </span>
          ))}
        </div>

        {/* ── Phase 0: Import Method ── */}
        <div className={`${styles.phaseContainer} ${currentStep === 0 ? styles.phaseContainerVisible : ''}`}>
          <div className={`${styles.card} ${styles.cardVisible}`}>
            <div className={styles.cardTitle}>
              <span className={styles.phaseBadge}>01</span>
              选择导入方式
            </div>
            <div className={styles.cardSubtitle}>
              已有 {TOTAL_CHAPTERS} 章内容待导入到系统，请选择你的导入方式。
            </div>

            <div className={styles.importOptions}>
              <div
                className={`${styles.importOption} ${importMethod === 'paste' ? styles.importOptionSelected : ''}`}
                onClick={() => setImportMethod('paste')}
              >
                <div className={styles.importOptionIcon}>
                  <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="var(--color-text-secondary)" strokeWidth="1.5" strokeLinecap="round">
                    <rect x="3" y="3" width="18" height="18" rx="2" />
                    <line x1="8" y1="9" x2="16" y2="9" />
                    <line x1="8" y1="13" x2="14" y2="13" />
                    <line x1="8" y1="17" x2="12" y2="17" />
                  </svg>
                </div>
                <div className={styles.importOptionTitle}>粘贴文本</div>
                <div className={styles.importOptionDesc}>直接复制已写好的章节内容，粘贴到输入框中</div>
              </div>
              <div
                className={`${styles.importOption} ${importMethod === 'file' ? styles.importOptionSelected : ''}`}
                onClick={() => setImportMethod('file')}
              >
                <div className={styles.importOptionIcon}>
                  <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="var(--color-text-secondary)" strokeWidth="1.5" strokeLinecap="round">
                    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                    <polyline points="14 2 14 8 20 8" />
                    <line x1="16" y1="13" x2="8" y2="13" />
                    <line x1="16" y1="17" x2="8" y2="17" />
                    <polyline points="10 9 9 9 8 9" />
                  </svg>
                </div>
                <div className={styles.importOptionTitle}>上传文件</div>
                <div className={styles.importOptionDesc}>上传 .txt 或 .docx 格式的文件，自动读取内容</div>
              </div>
            </div>

            {/* Paste Content */}
            <div className={`${styles.importContent} ${importMethod === 'paste' ? styles.importContentVisible : ''}`}>
              <textarea
                className={styles.pasteArea}
                placeholder={'将你已有的章节内容粘贴到这里…\n\n例如：\n第1章 星辰陨落\n苏铭站在玄天宗的山门前...'}
                value={pasteText}
                onChange={(e) => setPasteText(e.target.value)}
              />
              <div className={styles.pasteHint}>
                <span>建议每章用"第X章"标记分隔</span>
                <span className={styles.wordCount}>已输入 <span>{getWordCount(pasteText)}</span> 字</span>
              </div>
            </div>

            {/* File Upload Content */}
            <div className={`${styles.importContent} ${importMethod === 'file' ? styles.importContentVisible : ''}`}>
              <div
                className={`${styles.uploadArea} ${isDragOver ? styles.dragOver : ''}`}
                onDrop={handleDrop}
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onClick={handleClickUpload}
              >
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".txt,.docx"
                  style={{ display: 'none' }}
                  onChange={handleFileInputChange}
                />
                {uploading ? (
                  <div style={{ textAlign: 'center' }}>
                    <div className={styles.uploadIcon}>
                      <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="var(--color-brand-indigo)" strokeWidth="1.5">
                        <circle cx="12" cy="12" r="10" />
                        <polyline points="12 6 12 12 16 14" />
                      </svg>
                    </div>
                    <div className={styles.uploadTitle}>正在上传...</div>
                  </div>
                ) : (
                  <>
                    <div className={styles.uploadIcon}>
                      <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="var(--color-text-secondary)" strokeWidth="1.5" strokeLinecap="round">
                        <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                        <polyline points="17 8 12 3 7 8" />
                        <line x1="12" y1="3" x2="12" y2="15" />
                      </svg>
                    </div>
                    <div className={styles.uploadTitle}>拖拽文件到此处，或点击上传</div>
                    <div className={styles.uploadDesc}>支持 .txt 和 .docx 格式的文件</div>
                    <button className={styles.uploadBtn} onClick={(e) => { e.stopPropagation(); fileInputRef.current?.click(); }}>
                      选择文件
                    </button>
                    <div className={styles.uploadFormats}>支持的格式：.txt · .docx（最大 50MB）</div>
                  </>
                )}
              </div>

              {fileName && (
                <div className={`${styles.uploadFileInfo} ${styles.uploadFileInfoVisible}`}>
                  <div style={{ fontSize: '24px' }}>
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="var(--color-success)" strokeWidth="1.5">
                      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                      <polyline points="14 2 14 8 20 8" />
                    </svg>
                  </div>
                  <div>
                    <div className={styles.uploadFileName}>{fileName}</div>
                    <div className={styles.uploadFileSize}>{fileSize} · {TOTAL_CHAPTERS} 章</div>
                  </div>
                </div>
              )}
            </div>

            <div className={styles.continueRow}>
              <button
                className={styles.btnContinue}
                disabled={isProcessing || (importMethod === 'paste' && !pasteText.trim() && !uploading)}
                onClick={runAnalysis}
              >
                开始分析
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <polyline points="9 18 15 12 9 6" />
                </svg>
              </button>
            </div>
          </div>
        </div>

        {/* ── Phase 1: Full Library Analysis ── */}
        <div className={`${styles.phaseContainer} ${currentStep === 1 ? styles.phaseContainerVisible : ''}`}>
          <div className={`${styles.card} ${styles.cardVisible}`}>
            <div className={styles.cardTitle}>
              <span className={styles.phaseBadge}>02</span>
              全库分析 · 四库提取
            </div>
            <div className={styles.cardSubtitle}>
              LLM 正在分析全部 {TOTAL_CHAPTERS} 章内容，提取人物库、时间线库、剧情承诺库和世界观库。
            </div>

            <div className={styles.progressGrid}>
              {analysisItems.map((item) => (
                <div
                  key={item.key}
                  className={`${styles.progressItem} ${
                    item.status === 'pending' ? styles.progressItemPending :
                    item.status === 'active' ? styles.progressItemActive :
                    styles.progressItemDone
                  }`}
                >
                  <div className={styles.progressIcon}>
                    {item.status === 'done' ? (
                      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="var(--color-success)" strokeWidth="2.5" strokeLinecap="round">
                        <polyline points="20 6 9 17 4 12" />
                      </svg>
                    ) : (
                      <span>{libIcons[item.key]}</span>
                    )}
                  </div>
                  <div className={styles.progressItemInfo}>
                    <div className={styles.progressItemLabel}>{item.label}</div>
                    <div className={styles.progressItemStatus}>
                      {item.status === 'done' ? '✓ 提取完成' : item.status === 'active' ? '正在提取...' : '等待中...'}
                    </div>
                  </div>
                  {item.status === 'active' && <div className={styles.progressSpinner}></div>}
                </div>
              ))}
            </div>

            <div className={styles.overallProgress}>
              <div className={styles.progressBarTrack}>
                <div className={styles.progressBarFill} style={{ width: `${progressPercent}%` }}></div>
              </div>
              <div className={styles.progressStats}>
                <span>分析进度：<span className={styles.statValue}>{progress}/4</span></span>
                <span><span className={styles.statValue}>{progressPercent}%</span></span>
              </div>
            </div>
          </div>
        </div>

        {/* ── Phase 2: Dynamic Layer Analysis ── */}
        <div className={`${styles.phaseContainer} ${currentStep === 2 ? styles.phaseContainerVisible : ''}`}>
          <div className={`${styles.card} ${styles.cardVisible}`}>
            <div className={styles.cardTitle}>
              <span className={styles.phaseBadge}>03</span>
              近三章动态分析
            </div>
            <div className={styles.cardSubtitle}>
              聚焦最后 3 章（第 21-23 章），提取故事当前状态——即动态层数据。
            </div>

            <div className={styles.dynamicChapters}>
              {dynamicChapters.map((ch, i) => (
                <div key={i} className={styles.dynamicChapterCard}>
                  <div className={styles.dynamicChapterNumber}>{ch.number}</div>
                  <div className={styles.dynamicChapterTitle}>{ch.title}</div>
                  <ul className={styles.dynamicChapterEvents}>
                    {ch.events.map((evt, j) => <li key={j}>{evt}</li>)}
                  </ul>
                </div>
              ))}
            </div>

            <div className={styles.dynamicInsights}>
              <div className={styles.dynamicInsight}>
                <div className={styles.dynamicInsightIcon}>
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="var(--color-brand-indigo)" strokeWidth="1.5">
                    <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
                    <circle cx="12" cy="7" r="4" />
                  </svg>
                </div>
                <div className={styles.dynamicInsightContent}>
                  <div className={styles.dynamicInsightLabel}>当前 POV</div>
                  <div className={styles.dynamicInsightValue}>苏铭</div>
                </div>
              </div>
              <div className={styles.dynamicInsight}>
                <div className={styles.dynamicInsightIcon}>
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="var(--color-brand-indigo)" strokeWidth="1.5" strokeLinecap="round">
                    <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z" />
                    <circle cx="12" cy="10" r="3" />
                  </svg>
                </div>
                <div className={styles.dynamicInsightContent}>
                  <div className={styles.dynamicInsightLabel}>主要地点</div>
                  <div className={styles.dynamicInsightValue}>玄天宗秘境</div>
                </div>
              </div>
              <div className={styles.dynamicInsight}>
                <div className={styles.dynamicInsightIcon}>
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="var(--color-brand-indigo)" strokeWidth="1.5" strokeLinecap="round">
                    <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9" />
                    <path d="M13.73 21a2 2 0 0 1-3.46 0" />
                  </svg>
                </div>
                <div className={styles.dynamicInsightContent}>
                  <div className={styles.dynamicInsightLabel}>活跃钩子</div>
                  <div className={styles.dynamicInsightValue}>
                    <span className={`${styles.tag} ${styles.tagIndigo}`}>禁术残卷下落</span>
                    <span className={`${styles.tag} ${styles.tagIndigo}`}>王城地下的异响</span>
                  </div>
                </div>
              </div>
              <div className={styles.dynamicInsight}>
                <div className={styles.dynamicInsightIcon}>
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="var(--color-brand-indigo)" strokeWidth="1.5" strokeLinecap="round">
                    <polyline points="20 6 9 17 4 12" />
                  </svg>
                </div>
                <div className={styles.dynamicInsightContent}>
                  <div className={styles.dynamicInsightLabel}>连贯性基线</div>
                  <div className={styles.dynamicInsightValue}>
                    <span className={`${styles.tag} ${styles.tagGreen}`}>良好（时间线无矛盾）</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* ── Phase 3: Review ── */}
        <div className={`${styles.phaseContainer} ${currentStep === 3 ? styles.phaseContainerVisible : ''}`}>
          <div className={`${styles.card} ${styles.cardVisible}`}>
            <div className={styles.cardTitle}>
              <span className={styles.phaseBadge}>04</span>
              审查确认
            </div>
            <div className={styles.cardSubtitle}>
              以下是系统从 {TOTAL_CHAPTERS} 章中分析提取的四库数据摘要，请确认无误后导入。
            </div>

            <div className={styles.reviewSummary}>
              <div className={styles.reviewItem}>
                <div className={styles.reviewItemIcon}>
                  <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="var(--color-brand-indigo)" strokeWidth="1.5">
                    <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
                    <circle cx="12" cy="7" r="4" />
                  </svg>
                </div>
                <div className={styles.reviewItemCount}>12</div>
                <div className={styles.reviewItemLabel}>人物</div>
                <div className={styles.reviewItemSublabel}>苏铭、叶青寒、夜无痕...</div>
              </div>
              <div className={styles.reviewItem}>
                <div className={styles.reviewItemIcon}>
                  <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="var(--color-brand-indigo)" strokeWidth="1.5">
                    <rect x="3" y="4" width="18" height="18" rx="2" ry="2" />
                    <line x1="16" y1="2" x2="16" y2="6" />
                    <line x1="8" y1="2" x2="8" y2="6" />
                    <line x1="3" y1="10" x2="21" y2="10" />
                  </svg>
                </div>
                <div className={styles.reviewItemCount}>5</div>
                <div className={styles.reviewItemLabel}>时间节点</div>
                <div className={styles.reviewItemSublabel}>第1天 → 第23天</div>
              </div>
              <div className={styles.reviewItem}>
                <div className={styles.reviewItemIcon}>
                  <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="var(--color-brand-indigo)" strokeWidth="1.5" strokeLinecap="round">
                    <path d="M12 2L2 7l10 5 10-5-10-5z" />
                    <path d="M2 17l10 5 10-5" />
                    <path d="M2 12l10 5 10-5" />
                  </svg>
                </div>
                <div className={styles.reviewItemCount}>8</div>
                <div className={styles.reviewItemLabel}>剧情承诺</div>
                <div className={styles.reviewItemSublabel}>玉佩秘密、禁术残卷...</div>
              </div>
              <div className={styles.reviewItem}>
                <div className={styles.reviewItemIcon}>
                  <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="var(--color-brand-indigo)" strokeWidth="1.5" strokeLinecap="round">
                    <circle cx="12" cy="12" r="10" />
                    <line x1="2" y1="12" x2="22" y2="12" />
                    <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z" />
                  </svg>
                </div>
                <div className={styles.reviewItemCount}>6</div>
                <div className={styles.reviewItemLabel}>世界观条目</div>
                <div className={styles.reviewItemSublabel}>灵力体系、玄天宗...</div>
              </div>
            </div>

            {/* Conflicts */}
            {hasConflicts ? (
              <div className={styles.conflictsSection}>
                <div className={styles.conflictsTitle}>
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
                    <circle cx="12" cy="12" r="10" />
                    <line x1="12" y1="8" x2="12" y2="12" />
                    <line x1="12" y1="16" x2="12.01" y2="16" />
                  </svg>
                  发现 {conflicts.length} 项冲突
                </div>
                {conflicts.map((c, i) => (
                  <div key={i} className={styles.conflictItem}>
                    <span className={styles.conflictIcon}>
                      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="var(--color-danger)" strokeWidth="2" strokeLinecap="round">
                        <circle cx="12" cy="12" r="10" />
                        <line x1="12" y1="8" x2="12" y2="12" />
                        <line x1="12" y1="16" x2="12.01" y2="16" />
                      </svg>
                    </span>
                    <div className={styles.conflictText}>
                      <div className={styles.conflictTextMain}>{c.main}</div>
                      <div className={styles.conflictTextDetail}>{c.detail}</div>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className={styles.noConflicts}>
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
                  <polyline points="20 6 9 17 4 12" />
                </svg>
                <span>未检测到矛盾冲突，四库数据一致性良好。</span>
              </div>
            )}

            <div className={styles.reviewActions}>
              <button className={styles.btnSecondary} onClick={handleAbort}>放弃导入</button>
              <button className={styles.btnPrimary} onClick={handleConfirmImport} disabled={isProcessing}>
                {isProcessing ? '导入中...' : (
                  <>
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
                      <polyline points="20 6 9 17 4 12" />
                    </svg>
                    确认导入
                  </>
                )}
              </button>
            </div>
          </div>
        </div>

        {/* ── Phase 4: Completion ── */}
        <div className={`${styles.phaseContainer} ${currentStep === 4 ? styles.phaseContainerVisible : ''}`}>
          <div className={`${styles.card} ${styles.cardVisible}`}>
            <div className={styles.completionCard}>
              <div className={styles.completionIcon}>
                <svg width="56" height="56" viewBox="0 0 24 24" fill="none" stroke="var(--color-success)" strokeWidth="1.5" strokeLinecap="round">
                  <circle cx="12" cy="12" r="10" />
                  <polyline points="16 8 10 16 7 13" />
                </svg>
              </div>
              <div className={styles.completionTitle}>导入成功</div>
              <div className={styles.completionSubtitle}>
                已导入 {TOTAL_CHAPTERS} 章小说内容，系统已完成四库分析和动态层提取。<br />
                你可以直接进入创作工作台，开始第 24 章的写作。
              </div>
              <div className={styles.completionStats}>
                <div className={styles.completionStat}>
                  <div className={styles.completionStatValue}>{TOTAL_CHAPTERS}</div>
                  <div className={styles.completionStatLabel}>已导入章节</div>
                </div>
                <div className={styles.completionStat}>
                  <div className={styles.completionStatValue}>12</div>
                  <div className={styles.completionStatLabel}>提取人物</div>
                </div>
                <div className={styles.completionStat}>
                  <div className={styles.completionStatValue}>5</div>
                  <div className={styles.completionStatLabel}>时间线节点</div>
                </div>
                <div className={styles.completionStat}>
                  <div className={styles.completionStatValue}>8</div>
                  <div className={styles.completionStatLabel}>剧情承诺</div>
                </div>
                <div className={styles.completionStat}>
                  <div className={styles.completionStatValue}>6</div>
                  <div className={styles.completionStatLabel}>世界观条目</div>
                </div>
              </div>
              <div className={styles.completionActions}>
                <button className={styles.btnSecondary} onClick={() => window.history.back()}>
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
                    <polyline points="15 18 9 12 15 6" />
                  </svg>
                  返回作品列表
                </button>
                <button className={styles.btnPrimary} onClick={() => {/* navigate to workspace */}}>
                  进入创作工作台
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
                    <polyline points="9 18 15 12 9 6" />
                  </svg>
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );

  // ── Mobile View ──
  const mobileView = (
    <div className={styles.mobileShell}>
      <div className={styles.mStatusBar}>
        <span>9:41</span>
        <div style={{ display: 'flex', gap: '6px' }}>
          <svg width="16" height="12" viewBox="0 0 16 12" fill="currentColor" opacity="0.6">
            <rect x="0" y="6" width="3" height="6" rx="0.5" />
            <rect x="4" y="4" width="3" height="8" rx="0.5" />
            <rect x="8" y="2" width="3" height="10" rx="0.5" />
            <rect x="12" y="0" width="3" height="12" rx="0.5" opacity="0.3" />
          </svg>
          <svg width="25" height="12" viewBox="0 0 25 12" fill="currentColor">
            <rect x="0" y="1" width="21" height="10" rx="2" fill="none" stroke="currentColor" strokeWidth="1" />
            <rect x="1.5" y="2.5" width="14" height="7" rx="1" fill="#34d399" />
            <rect x="22" y="4" width="2" height="4" rx="0.5" />
          </svg>
        </div>
      </div>

      <div className={styles.mTopNav}>
        <button className={styles.mBackBtn} onClick={() => { if (confirm('返回后将丢失当前进度，确定返回吗？')) window.history.back(); }}>
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
            <polyline points="15 18 9 12 15 6" />
          </svg>
        </button>
        <span className={styles.mNavTitle}>导入已有小说</span>
      </div>

      <div className={styles.mStepBar}>
        {steps.map((step, i) => (
          <div key={i} className={`${styles.mStepItem} ${step.active ? styles.mStepItemActive : ''} ${step.done ? styles.mStepItemDone : ''}`}>
            <div className={styles.mStepDot}>{i + 1}</div>
            <span className={styles.mStepLabel}>{step.label}</span>
            {i < steps.length - 1 && <div className={styles.mStepLine}></div>}
          </div>
        ))}
      </div>

      <div className={styles.mMainContent}>
        {/* Phase 0 */}
        <div className={`${styles.mPhase} ${currentStep === 0 ? styles.mPhaseVisible : ''}`}>
          <div className={styles.mImportOptions}>
            <div className={`${styles.mImportOpt} ${importMethod === 'paste' ? styles.mImportOptSelected : ''}`} onClick={() => setImportMethod('paste')}>
              <div className={styles.mOptIcon}>
                <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="var(--color-text-primary)" strokeWidth="1.5" strokeLinecap="round">
                  <rect x="3" y="3" width="18" height="18" rx="2" />
                  <line x1="8" y1="9" x2="16" y2="9" />
                  <line x1="8" y1="13" x2="14" y2="13" />
                  <line x1="8" y1="17" x2="12" y2="17" />
                </svg>
              </div>
              <div className={styles.mOptTitle}>粘贴文本</div>
              <div className={styles.mOptDesc}>粘贴章节正文，系统自动识别章节结构</div>
            </div>

            <div className={`${styles.mPasteArea} ${importMethod === 'paste' ? styles.mPasteAreaShow : ''}`}>
              <textarea
                placeholder="在此粘贴小说文本…"
                value={pasteText}
                onChange={(e) => setPasteText(e.target.value)}
              />
            </div>

            <div className={`${styles.mImportOpt} ${importMethod === 'file' ? styles.mImportOptSelected : ''}`} onClick={() => setImportMethod('file')}>
              <div className={styles.mOptIcon}>
                <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="var(--color-text-primary)" strokeWidth="1.5" strokeLinecap="round">
                  <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                  <polyline points="14 2 14 8 20 8" />
                </svg>
              </div>
              <div className={styles.mOptTitle}>上传文件</div>
              <div className={styles.mOptDesc}>支持 .txt / .docx 格式</div>
            </div>

            <div className={`${styles.mUploadZone} ${importMethod === 'file' ? styles.mUploadZoneShow : ''}`}>
              <div className={styles.mUploadDrop} onClick={handleClickUpload}>
                <input
                  type="file"
                  accept=".txt,.docx"
                  style={{ display: 'none' }}
                  ref={fileInputRef}
                  onChange={handleFileInputChange}
                />
                点击选择文件或拖拽至此<br />
                <span style={{ fontSize: '12px', color: 'var(--color-text-tertiary)' }}>支持 .txt, .docx</span>
              </div>
            </div>
          </div>
          <button
            className={`${styles.mBigBtn} ${styles.mBigBtnBrand}`}
            disabled={importMethod === 'paste' && !pasteText.trim()}
            onClick={runAnalysis}
          >
            开始分析
          </button>
        </div>

        {/* Phase 1 */}
        <div className={`${styles.mPhase} ${currentStep === 1 ? styles.mPhaseVisible : ''}`}>
          <div className={styles.mAnalysisList}>
            {analysisItems.map((item) => (
              <div
                key={item.key}
                className={`${styles.mAnalysisItem} ${item.status === 'done' ? styles.mAnalysisItemDone : ''}`}
              >
                <div className={styles.mAnalysisIcon}>
                  {item.status === 'done' ? (
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="var(--color-success)" strokeWidth="2.5" strokeLinecap="round">
                      <polyline points="20 6 9 17 4 12" />
                    </svg>
                  ) : (
                    <span>{item.key === 'characters' ? '👤' : item.key === 'timeline' ? '📅' : item.key === 'commitments' ? '🔗' : '🌍'}</span>
                  )}
                </div>
                <span className={styles.mAnalysisText}>{item.label}</span>
                <span className={styles.mAnalysisStatus}>
                  {item.status === 'active' ? <div className={styles.mSpinner}></div> :
                   item.status === 'done' ? '✓' : '等待'}
                </span>
              </div>
            ))}
          </div>
          <div className={styles.mProgressTrack}>
            <div className={styles.mProgressFill} style={{ width: `${progressPercent}%` }}></div>
          </div>
          <div className={styles.mProgressLabel}>分析进度：{progress}/4</div>
        </div>

        {/* Phase 2 */}
        <div className={`${styles.mPhase} ${currentStep === 2 ? styles.mPhaseVisible : ''}`}>
          <div style={{ fontSize: '16px', fontWeight: 600, color: 'var(--color-text-secondary)', marginBottom: '14px' }}>
            近三章动态分析（第21-23章）
          </div>
          <div style={{ display: 'flex', gap: '12px', overflowX: 'auto', paddingBottom: '8px', marginBottom: '20px' }}>
            {dynamicChapters.map((ch, i) => (
              <div key={i} style={{ minWidth: '160px', background: 'var(--color-surface)', borderRadius: '14px', padding: '16px', border: '1px solid rgba(99,102,241,0.08)' }}>
                <div style={{ fontSize: '12px', color: 'var(--color-brand-indigo)', fontWeight: 600, marginBottom: '6px' }}>{ch.number}</div>
                <div style={{ fontSize: '14px', fontWeight: 600, marginBottom: '6px' }}>{ch.title}</div>
                <div style={{ fontSize: '12px', color: 'var(--color-text-secondary)', lineHeight: '1.5' }}>{ch.events.join('；')}</div>
              </div>
            ))}
          </div>
        </div>

        {/* Phase 3 */}
        <div className={`${styles.mPhase} ${currentStep === 3 ? styles.mPhaseVisible : ''}`}>
          <div style={{ background: 'var(--color-surface)', borderRadius: '14px', padding: '20px', marginBottom: '16px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '16px', fontSize: '16px', fontWeight: 600 }}>
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="var(--color-brand-indigo)" strokeWidth="2" strokeLinecap="round">
                <rect x="3" y="3" width="18" height="18" rx="2" />
                <line x1="3" y1="9" x2="21" y2="9" />
              </svg>
              四库摘要
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
              {[
                { value: '12', label: '人物' },
                { value: '5', label: '时间线节点' },
                { value: '8', label: '剧情承诺' },
                { value: '6', label: '世界观' },
              ].map((item, i) => (
                <div key={i} style={{ background: 'var(--color-elevated)', borderRadius: '10px', padding: '14px', textAlign: 'center' }}>
                  <div style={{ fontSize: '22px', fontWeight: 700, color: 'var(--color-brand-indigo)' }}>{item.value}</div>
                  <div style={{ fontSize: '11px', color: 'var(--color-text-tertiary)', marginTop: '2px' }}>{item.label}</div>
                </div>
              ))}
            </div>
          </div>

          <div style={{ background: 'rgba(239,68,68,0.06)', border: '1px solid rgba(239,68,68,0.15)', borderRadius: '14px', padding: '18px', marginBottom: '20px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '14px', fontSize: '15px', fontWeight: 600, color: 'var(--color-danger)' }}>
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
                <circle cx="12" cy="12" r="10" />
                <line x1="12" y1="8" x2="12" y2="12" />
                <line x1="12" y1="16" x2="12.01" y2="16" />
              </svg>
              冲突标记
            </div>
            <div style={{ display: 'flex', alignItems: 'flex-start', gap: '10px', padding: '10px 0', borderBottom: '1px solid rgba(239,68,68,0.08)', fontSize: '13px' }}>
              <div style={{ width: '8px', height: '8px', borderRadius: '50%', background: 'var(--color-danger)', flexShrink: 0, marginTop: '5px' }}></div>
              <div style={{ color: 'var(--color-text-secondary)' }}>
                叶青寒受伤后参战
                <span style={{ display: 'inline-block', background: 'rgba(239,68,68,0.12)', color: 'var(--color-danger)', fontSize: '11px', padding: '2px 8px', borderRadius: '6px', marginLeft: '4px' }}>时间线矛盾</span>
              </div>
            </div>
            <div style={{ display: 'flex', alignItems: 'flex-start', gap: '10px', padding: '10px 0', fontSize: '13px' }}>
              <div style={{ width: '8px', height: '8px', borderRadius: '50%', background: 'var(--color-danger)', flexShrink: 0, marginTop: '5px' }}></div>
              <div style={{ color: 'var(--color-text-secondary)' }}>
                王城异响未回收
                <span style={{ display: 'inline-block', background: 'rgba(239,68,68,0.12)', color: 'var(--color-danger)', fontSize: '11px', padding: '2px 8px', borderRadius: '6px', marginLeft: '4px' }}>承诺悬置</span>
              </div>
            </div>
          </div>

          <button className={`${styles.mBigBtn} ${styles.mBigBtnBrand}`} onClick={handleConfirmImport}>确认导入</button>
          <div
            style={{ display: 'block', textAlign: 'center', marginTop: '14px', color: 'var(--color-text-tertiary)', fontSize: '14px', cursor: 'pointer', padding: '8px' }}
            onClick={handleAbort}
          >
            放弃
          </div>
        </div>
      </div>
    </div>
  );

  return (
    <>
      {desktopView}
      {mobileView}
    </>
  );
}
