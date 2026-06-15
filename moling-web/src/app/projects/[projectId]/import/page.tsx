"use client";

import { useState, useCallback, useRef, use, useEffect } from "react";
import { useRouter } from "next/navigation";
import styles from "./page.module.css";
import { importApi } from "@/lib/api";

/* ─── Types ─── */

type ImportMethod = "paste" | "file" | null;
type ProgressStatus = "pending" | "active" | "done";
type JobStatus = "pending" | "running" | "phase1_done" | "phase2_done" | "completed" | "failed";

interface ProgressItem {
  id: string;
  label: string;
  icon: string;
  status: ProgressStatus;
  result: string;
}

interface ConflictItem {
  main: string;
  detail: string;
}

interface DynamicLayer {
  pov: string;
  location: string;
  hooks: string[];
  baseline: string;
}

interface ChapterData {
  number: number;
  title: string;
  events: string[];
}

/* ─── Mock Data ─── */

const MOCK = {
  novelName: "星穹之下",
  totalChapters: 23,
  characters: ["苏铭", "叶青寒", "夜无痕"],
  timeline: "第1天 → 第23天",
  commitmentsList: ["玉佩秘密", "禁术残卷", "七国密约"],
  worldItems: ["灵力体系", "玄天宗", "后山禁地"],
  dynamicLayer: {
    pov: "苏铭",
    location: "玄天宗秘境",
    hooks: ["禁术残卷下落", "王城地下的异响"],
    baseline: "良好（时间线无矛盾）",
  } as DynamicLayer,
  conflicts: [
    {
      main: "人物「叶青寒」在第 15 章受伤，但第 18 章参与战斗",
      detail:
        "时间线矛盾：叶青寒伤势较重，按设定第 16-17 章应在养伤，第 18 章突然出现在战场未被解释。",
    },
    {
      main: "王城地下异响在第 10 章埋设后未在第 20-23 章回收",
      detail:
        "剧情承诺未收束：该悬念间隔 10 章未提及，建议在后续章节中适时回收。",
    },
  ] as ConflictItem[],
  chapters: [
    { number: 21, title: "秘境入口", events: ["苏铭发现玄天宗秘境入口", "与叶青寒对峙，得到禁术残卷线索", "夜无痕暗中跟随"] },
    { number: 22, title: "禁地交锋", events: ["苏铭在秘境中遭遇守护兽", "叶青寒出手相助，伤势恶化", "发现王城地下有异响"] },
    { number: 23, title: "七国密约浮现", events: ["苏铭解封部分禁术残卷", "神秘人现身，警告七国势力已渗入", "玄天宗掌门召集紧急会议"] },
  ] as ChapterData[],
};

const INITIAL_PROGRESS: ProgressItem[] = [
  { id: "characters", label: "人物库提取", icon: "👥", status: "pending", result: "12 人" },
  { id: "timeline", label: "时间线库提取", icon: "⏱️", status: "pending", result: "5 个节点" },
  { id: "commitments", label: "剧情承诺库提取", icon: "📖", status: "pending", result: "8 项" },
  { id: "worldview", label: "世界观库提取", icon: "🌍", status: "pending", result: "6 项" },
];

const DEMO_PASTE_TEXT = `第1章 星辰陨落
苏铭站在玄天宗的山门前，抬头望着那块刻着古老符文的白玉石碑。今天是他入宗的第七天，也是最关键的一天——灵力考核。

第2章 初露锋芒
演武场上，数百名新弟子整齐列阵。苏铭站在人群中，手心微微冒汗。

第3章 玉佩之谜
夜深人静之时，苏铭独自坐在房中，手中握着一枚温润的玉佩——那是母亲留给他的唯一遗物。`;

function getPhaseLabel(idx: number): string {
  const labels = ["导入方式", "全库分析", "动态层", "审查确认"];
  return labels[idx] ?? "";
}

/* ─── Component ─── */

export default function ImportPage({ params }: { params: Promise<{ projectId: string }> }) {
  const { projectId } = use(params);
  const router = useRouter();

  // ── State ──
  const [phase, setPhase] = useState(0); // 0-4
  const [importMethod, setImportMethod] = useState<ImportMethod>(null);
  const [pasteText, setPasteText] = useState(DEMO_PASTE_TEXT);
  const [uploadFile, setUploadFile] = useState<{ name: string; size: string } | null>(null);
  const [progressItems, setProgressItems] = useState<ProgressItem[]>(INITIAL_PROGRESS);
  const [overallDone, setOverallDone] = useState(0);
  const [isProcessing, setIsProcessing] = useState(false);

  // API 集成相关状态
  const [jobId, setJobId] = useState<string | null>(null);
  const [importResult, setImportResult] = useState<{
    characters?: number;
    timeline?: number;
    commitments?: number;
    world?: number;
    conflicts?: ConflictItem[];
    dynamicLayer?: DynamicLayer;
    chapters?: ChapterData[];
    novelName?: string;
    totalChapters?: number;
  } | null>(null);

  const fileInputRef = useRef<HTMLInputElement>(null);
  const mFileInputRef = useRef<HTMLInputElement>(null);
  const pollIntervalRef = useRef<NodeJS.Timeout | null>(null);

  // 使用 API 结果或 mock 数据的辅助函数
  const getData = (): {
    novelName: string;
    totalChapters: number;
    characters: number;
    timeline: number;
    commitments: number;
    world: number;
    conflicts: ConflictItem[];
    chapters: ChapterData[];
    dynamicLayer: DynamicLayer;
  } => {
    if (importResult) {
      return {
        novelName: importResult.novelName || MOCK.novelName,
        totalChapters: importResult.totalChapters || MOCK.totalChapters,
        characters: importResult.characters ?? 0,
        timeline: importResult.timeline ?? 0,
        commitments: importResult.commitments ?? 0,
        world: importResult.world ?? 0,
        conflicts: importResult.conflicts || MOCK.conflicts,
        chapters: importResult.chapters || MOCK.chapters,
        dynamicLayer: importResult.dynamicLayer || MOCK.dynamicLayer,
      };
    }
    return {
      novelName: MOCK.novelName,
      totalChapters: MOCK.totalChapters,
      characters: 12,
      timeline: 5,
      commitments: 8,
      world: 6,
      conflicts: MOCK.conflicts,
      chapters: MOCK.chapters,
      dynamicLayer: MOCK.dynamicLayer,
    };
  };

  // ── Desktop: Word count ──
  const charCount = pasteText.replace(/\s/g, "").length;

  // ── File handling ──
  const handleFile = useCallback((file: File) => {
    const sizeKB = (file.size / 1024).toFixed(0);
    setUploadFile({ name: file.name, size: `${sizeKB} KB · 23 章（模拟）` });
  }, []);

  const onFileInputChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      if (e.target.files && e.target.files.length > 0) {
        handleFile(e.target.files[0]);
      }
    },
    [handleFile]
  );

  const onFileDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      if (e.dataTransfer.files.length > 0) {
        handleFile(e.dataTransfer.files[0]);
      }
    },
    [handleFile]
  );

/* ─── API 集成函数 ─── */

// 轮询导入任务状态 (API 7.2)
const startPolling = useCallback((pid: string, jid: string) => {
  // 清除之前的轮询
  if (pollIntervalRef.current) {
    clearInterval(pollIntervalRef.current);
  }

  pollIntervalRef.current = setInterval(async () => {
    try {
      const res = await importApi.getJobStatus(pid, jid);
      const job = res.data;

      // 更新进度显示
      if (job.progress !== undefined) {
        setOverallDone(Math.floor(job.progress / 25)); // 4 阶段，每阶段 25%
      }

      if (job.status === "completed" || job.status === "phase1_done" || job.status === "phase2_done") {
        // 停止轮询
        if (pollIntervalRef.current) {
          clearInterval(pollIntervalRef.current);
          pollIntervalRef.current = null;
        }

        // 获取导入结果
        try {
          const resultRes = await importApi.getImportResult(pid, jid);
          setImportResult({
            characters: resultRes.data.characters_created,
            timeline: resultRes.data.events_created,
            commitments: resultRes.data.commitments_created,
            world: resultRes.data.entries_created,
          });
        } catch {
          // 如果 result 端点不存在，使用 job.result 并映射字段名
          if (job.result) {
            const r = job.result;
            setImportResult({
              characters: r.characters_created ?? 0,
              timeline: r.events_created ?? 0,
              commitments: r.commitments_created ?? 0,
              world: r.entries_created ?? 0,
            });
          }
        }

        setPhase(3);
        setIsProcessing(false);
      } else if (job.status === "failed") {
        if (pollIntervalRef.current) {
          clearInterval(pollIntervalRef.current);
          pollIntervalRef.current = null;
        }
        alert(`导入失败: ${job.error || "未知错误"}`);
        setIsProcessing(false);
        setPhase(0);
      }
    } catch (err) {
      console.error("轮询导入状态失败:", err);
    }
  }, 2000); // 2秒轮询间隔，符合接口文档建议
}, []);

// 开始导入流程 (API 7.1 + 7.3)
const startImport = useCallback(async (pid: string, text: string) => {
  setIsProcessing(true);
  setPhase(1);

  try {
    // 7.1 提交导入任务
    const createRes = await importApi.createJob(pid, { text, source_type: "paste" });
    const jid = createRes.data.job_id;
    setJobId(jid);

    // 7.3 执行 Phase 1（四库提取）
    await importApi.runPhase1(pid, jid);

    // 7.4 执行 Phase 2（动态层分析）
    await importApi.runPhase2(pid, jid);

    // 开始轮询进度 (API 7.2)
    startPolling(pid, jid);
  } catch (err) {
    console.error("导入失败:", err);
    alert("导入失败，请重试");
    setIsProcessing(false);
    setPhase(0);
  }
}, [startPolling]);

// ── Desktop Import Flow ──
const dStartImport = useCallback(async () => {
  if (isProcessing) return;

  if (importMethod === "paste" && pasteText.trim()) {
    await startImport(projectId, pasteText);
  } else if (importMethod === "file" && uploadFile) {
    // 文件上传模式
    setIsProcessing(true);
    setPhase(1);
    // TODO: 实现文件上传，使用 importApi.uploadAndImport
    alert("文件上传功能开发中");
    setIsProcessing(false);
    setPhase(0);
  } else {
    alert("请选择导入方式并输入内容");
  }
}, [isProcessing, importMethod, pasteText, uploadFile, projectId, startImport]);

// ── Mobile Import Flow ──
const mStartAnalysis = useCallback(() => {
  if (importMethod === null) return;

  if (importMethod === "paste" && pasteText.trim()) {
    startImport(projectId, pasteText);
  } else if (importMethod === "file" && uploadFile) {
    alert("文件上传功能开发中");
  } else {
    alert("请选择导入方式并输入内容");
  }
}, [importMethod, pasteText, uploadFile, projectId, startImport]);

// ── Confirm Import (API 7.5) ──
const confirmImport = useCallback(async () => {
  if (!jobId || isProcessing) return;
  setIsProcessing(true);

  try {
    const res = await importApi.confirmImport(projectId, jobId);
    if (res.data.confirmed) {
      setPhase(4);
      // 3秒后自动跳转到工作台
      setTimeout(() => {
        router.push(`/workspace/${projectId}`);
      }, 3000);
    } else {
      alert("确认导入失败");
    }
  } catch (err) {
    console.error("确认导入失败:", err);
    alert("确认导入失败，请重试");
  } finally {
    setIsProcessing(false);
  }
}, [jobId, isProcessing, projectId, router]);

// ── Desktop Confirm Import ──
const dConfirmImport = useCallback(() => {
  confirmImport();
}, [confirmImport]);

// ── Mobile Confirm Import ──
const mConfirmImport = useCallback(() => {
  confirmImport();
}, [confirmImport]);

// ── Abort Import ──
const resetAll = useCallback(() => {
  // 清除轮询
  if (pollIntervalRef.current) {
    clearInterval(pollIntervalRef.current);
    pollIntervalRef.current = null;
  }
  setPhase(0);
  setProgressItems(INITIAL_PROGRESS);
  setOverallDone(0);
  setIsProcessing(false);
  setImportMethod(null);
  setUploadFile(null);
  setJobId(null);
  setImportResult(null);
}, []);

// 组件卸载时清理轮询
useEffect(() => {
  return () => {
    if (pollIntervalRef.current) {
      clearInterval(pollIntervalRef.current);
    }
  };
}, []);

  // ── Navigation ──
  const goBack = useCallback(() => {
    router.push(`/projects/${projectId}`);
  }, [router, projectId]);

  const goToWorkspace = useCallback(() => {
    router.push(`/workspace/${projectId}`);
  }, [router, projectId]);

  // ── Derived ──
  const data = getData();
  const pct = Math.min(Math.round((overallDone / 4) * 100), 100);

  // ═══════════════════════════════════════════════════════
  // Render
  // ═══════════════════════════════════════════════════════
  return (
    <>
      {/* ╔═══════════════════════════════════════════════════════╗
           ║  DESKTOP SHELL                                        ║
           ╚═══════════════════════════════════════════════════════╝ */}
      <div className={styles.desktopShell}>
        {/* ── Header ── */}
        <header className={styles.header}>
          <button className={styles.headerBackBtn} onClick={goBack} title="返回我的作品">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
              <polyline points="15 18 9 12 15 6" />
            </svg>
          </button>
          <span className={styles.headerTitle}>导入已有小说</span>
          <div className={styles.headerSpacer} />
          <div className={styles.headerProject}>
            <span className={styles.projectDot} />
            <span className={styles.projectName}>{data.novelName}</span>
            <span style={{ fontSize: 11, color: "var(--color-text-disabled)" }}>
              {data.totalChapters}章
            </span>
          </div>
        </header>

        {/* ── Main Scroll Area ── */}
        <div className={styles.mainScroll}>
          {/* ── Step Indicator ── */}
          <div className={styles.stepIndicator}>
            {[0, 1, 2].map((stepIdx) => (
              <div key={`group-${stepIdx}`} style={{ display: "contents" }}>
                <div
                  className={`${styles.stepNode} ${
                    phase > stepIdx || phase === 4 ? styles.stepDone : phase === stepIdx ? styles.stepActive : ""
                  }`}
                >
                  <div className={styles.stepCircle}>{stepIdx + 1}</div>
                  <span className={styles.stepLabel}>{getPhaseLabel(stepIdx)}</span>
                </div>
                <div
                  className={`${styles.stepConnector} ${
                    phase > stepIdx || phase === 4 ? styles.connectorDone : ""
                  }`}
                />
              </div>
            ))}
            <div
              className={`${styles.stepNode} ${
                phase === 4 || phase > 3 ? styles.stepDone : phase === 3 ? styles.stepActive : ""
              }`}
            >
              <div className={styles.stepCircle}>4</div>
              <span className={styles.stepLabel}>{getPhaseLabel(3)}</span>
            </div>
          </div>

          {/* ══════════════════════════════════════════════════
              Phase 0: 选择导入方式
              ══════════════════════════════════════════════════ */}
          <div className={`${styles.phaseContainer} ${phase === 0 ? styles.phaseVisible : ""}`}>
            <div className={styles.card}>
              <div className={styles.cardTitle}>
                <span className={styles.phaseBadge}>01</span>
                选择导入方式
              </div>
              <div className={styles.cardSubtitle}>
                已有 {data.totalChapters} 章内容待导入到系统，请选择你的导入方式。
              </div>

              <div className={styles.importOptions}>
                <div
                  className={`${styles.importOption} ${importMethod === "paste" ? styles.optionSelected : ""}`}
                  onClick={() => setImportMethod("paste")}
                >
                  <div className={styles.optIcon}>📋</div>
                  <div className={styles.optTitle}>粘贴文本</div>
                  <div className={styles.optDesc}>直接复制已写好的章节内容，粘贴到输入框中</div>
                </div>
                <div
                  className={`${styles.importOption} ${importMethod === "file" ? styles.optionSelected : ""}`}
                  onClick={() => setImportMethod("file")}
                >
                  <div className={styles.optIcon}>📁</div>
                  <div className={styles.optTitle}>上传文件</div>
                  <div className={styles.optDesc}>上传 .txt 或 .docx 格式的文件，自动读取内容</div>
                </div>
              </div>

              {/* Paste Content */}
              <div className={`${styles.importContent} ${importMethod === "paste" ? styles.contentVisible : ""}`}>
                <textarea
                  className={styles.pasteArea}
                  placeholder="将你已有的章节内容粘贴到这里…"
                  value={pasteText}
                  onChange={(e) => setPasteText(e.target.value)}
                />
                <div className={styles.pasteHint}>
                  <span>建议每章用&ldquo;第X章&rdquo;标记分隔</span>
                  <span className={styles.wordCount}>
                    已输入 <span>{charCount}</span> 字
                  </span>
                </div>
              </div>

              {/* File Upload Content */}
              <div className={`${styles.importContent} ${importMethod === "file" ? styles.contentVisible : ""}`}>
                <div
                  className={styles.uploadArea}
                  onDragOver={(e) => e.preventDefault()}
                  onDrop={onFileDrop}
                  onClick={() => fileInputRef.current?.click()}
                >
                  <div className={styles.uploadIcon}>📂</div>
                  <div className={styles.uploadTitle}>拖拽文件到此处，或点击上传</div>
                  <div className={styles.uploadDesc}>支持 .txt 和 .docx 格式的文件</div>
                  <button
                    className={styles.uploadBtn}
                    onClick={(e) => {
                      e.stopPropagation();
                      fileInputRef.current?.click();
                    }}
                  >
                    选择文件
                  </button>
                  <div className={styles.uploadFormats}>支持的格式：.txt · .docx（最大 50MB）</div>
                </div>
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".txt,.docx"
                  style={{ display: "none" }}
                  onChange={onFileInputChange}
                />
                {uploadFile && (
                  <div className={`${styles.uploadFileInfo} ${styles.fileInfoVisible}`}>
                    <span className={styles.fileIcon}>📄</span>
                    <div>
                      <div className={styles.fileName}>{uploadFile.name}</div>
                      <div className={styles.fileSize}>{uploadFile.size}</div>
                    </div>
                  </div>
                )}
              </div>

              <div className={styles.continueRow}>
                <button
                  className={styles.btnContinue}
                  disabled={importMethod === null || isProcessing}
                  onClick={dStartImport}
                >
                  {isProcessing ? "分析中..." : "开始分析"}
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <polyline points="9 18 15 12 9 6" />
                  </svg>
                </button>
              </div>
            </div>
          </div>

          {/* ══════════════════════════════════════════════════
              Phase 1: 全库分析
              ══════════════════════════════════════════════════ */}
          <div className={`${styles.phaseContainer} ${phase === 1 ? styles.phaseVisible : ""}`}>
            <div className={styles.card}>
              <div className={styles.cardTitle}>
                <span className={styles.phaseBadge}>02</span>
                全库分析 · 四库提取
              </div>
              <div className={styles.cardSubtitle}>
                LLM 正在分析全部 {data.totalChapters} 章内容，提取人物库、时间线库、剧情承诺库和世界观库。
              </div>

              <div className={styles.progressGrid}>
                {progressItems.map((item) => (
                  <div
                    key={item.id}
                    className={`${styles.progressItem} ${
                      item.status === "pending"
                        ? styles.itemPending
                        : item.status === "active"
                        ? styles.itemActive
                        : styles.itemDone
                    }`}
                  >
                    <div className={styles.progressIcon}>{item.status === "done" ? "✅" : item.icon}</div>
                    <div className={styles.itemInfo}>
                      <div className={styles.itemLabel}>{item.label}</div>
                      <div className={styles.itemStatus}>
                        {item.status === "pending"
                          ? "等待中..."
                          : item.status === "active"
                          ? "正在提取..."
                          : "✓ 提取完成"}
                      </div>
                    </div>
                    {item.status === "active" && <div className={styles.progressSpinner} />}
                  </div>
                ))}
              </div>

              <div className={styles.overallProgress}>
                <div className={styles.progressTrack}>
                  <div className={styles.progressFill} style={{ width: `${pct}%` }} />
                </div>
                <div className={styles.progressStats}>
                  <span>
                    分析进度：<span className={styles.statValue}>{overallDone}/4</span>
                  </span>
                  <span>
                    <span className={styles.statValue}>{pct}%</span>
                  </span>
                </div>
              </div>
            </div>
          </div>

          {/* ══════════════════════════════════════════════════
              Phase 2: 动态层分析
              ══════════════════════════════════════════════════ */}
          <div className={`${styles.phaseContainer} ${phase === 2 ? styles.phaseVisible : ""}`}>
            <div className={styles.card}>
              <div className={styles.cardTitle}>
                <span className={styles.phaseBadge}>03</span>
                近三章动态分析
              </div>
              <div className={styles.cardSubtitle}>
                聚焦最后 3 章（第 21-23 章），提取故事当前状态——即动态层数据。
              </div>

              <div className={styles.dynamicChapters}>
                {data.chapters.map((ch) => (
                  <div key={ch.number} className={styles.chapterCard}>
                    <div className={styles.chapterNumber}>第 {ch.number} 章</div>
                    <div className={styles.chapterTitle}>{ch.title}</div>
                    <ul className={styles.chapterEvents}>
                      {ch.events.map((ev, i) => (
                        <li key={i}>{ev}</li>
                      ))}
                    </ul>
                  </div>
                ))}
              </div>

              <div className={styles.dynamicInsights}>
                <div className={styles.insightItem}>
                  <div className={styles.insightIcon}>🎯</div>
                  <div className={styles.insightContent}>
                    <div className={styles.insightLabel}>当前 POV</div>
                    <div className={styles.insightValue}>{data.dynamicLayer.pov}</div>
                  </div>
                </div>
                <div className={styles.insightItem}>
                  <div className={styles.insightIcon}>📍</div>
                  <div className={styles.insightContent}>
                    <div className={styles.insightLabel}>主要地点</div>
                    <div className={styles.insightValue}>{data.dynamicLayer.location}</div>
                  </div>
                </div>
                <div className={styles.insightItem}>
                  <div className={styles.insightIcon}>🪝</div>
                  <div className={styles.insightContent}>
                    <div className={styles.insightLabel}>活跃钩子</div>
                    <div className={styles.insightValue}>
                      {data.dynamicLayer.hooks.map((h, i) => (
                        <span key={i} className={`${styles.tag} ${styles.tagIndigo}`}>
                          {h}
                        </span>
                      ))}
                    </div>
                  </div>
                </div>
                <div className={styles.insightItem}>
                  <div className={styles.insightIcon}>📊</div>
                  <div className={styles.insightContent}>
                    <div className={styles.insightLabel}>连贯性基线</div>
                    <div className={styles.insightValue}>
                      <span className={`${styles.tag} ${styles.tagGreen}`}>{data.dynamicLayer.baseline}</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* ══════════════════════════════════════════════════
              Phase 3: 审查确认
              ══════════════════════════════════════════════════ */}
          <div className={`${styles.phaseContainer} ${phase === 3 ? styles.phaseVisible : ""}`}>
            <div className={styles.card}>
              <div className={styles.cardTitle}>
                <span className={styles.phaseBadge}>04</span>
                审查确认
              </div>
              <div className={styles.cardSubtitle}>
                以下是系统从 {data.totalChapters} 章中分析提取的四库数据摘要，请确认无误后导入。
              </div>

              <div className={styles.reviewSummary}>
                <div className={styles.reviewItem}>
                  <div className={styles.revIcon}>👥</div>
                  <div className={styles.revCount}>{data.characters}</div>
                  <div className={styles.revLabel}>人物</div>
                  <div className={styles.revSublabel}>已提取</div>
                </div>
                <div className={styles.reviewItem}>
                  <div className={styles.revIcon}>⏱️</div>
                  <div className={styles.revCount}>{data.timeline}</div>
                  <div className={styles.revLabel}>时间节点</div>
                  <div className={styles.revSublabel}>已提取</div>
                </div>
                <div className={styles.reviewItem}>
                  <div className={styles.revIcon}>📖</div>
                  <div className={styles.revCount}>{data.commitments}</div>
                  <div className={styles.revLabel}>剧情承诺</div>
                  <div className={styles.revSublabel}>已提取</div>
                </div>
                <div className={styles.reviewItem}>
                  <div className={styles.revIcon}>🌍</div>
                  <div className={styles.revCount}>{data.world}</div>
                  <div className={styles.revLabel}>世界观条目</div>
                  <div className={styles.revSublabel}>已提取</div>
                </div>
              </div>

              <div className={styles.conflictsSection}>
                <div className={styles.conflictsTitle}>⚠️ 发现 {data.conflicts.length} 项冲突</div>
                {data.conflicts.map((c, i) => (
                  <div key={i} className={styles.conflictItem}>
                    <span className={styles.conflictIcon}>⚠️</span>
                    <div className={styles.conflictText}>
                      <div className={styles.conflictMain}>{c.main}</div>
                      <div className={styles.conflictDetail}>{c.detail}</div>
                    </div>
                  </div>
                ))}
              </div>

              <div className={styles.reviewActions}>
                <button className={styles.btnSecondary} onClick={resetAll}>
                  放弃导入
                </button>
                <button className={styles.btnPrimary} onClick={dConfirmImport} disabled={isProcessing}>
                  {isProcessing ? "导入中..." : "✓ 确认导入"}
                </button>
              </div>
            </div>
          </div>

          {/* ══════════════════════════════════════════════════
              Phase 4: 导入完成
              ══════════════════════════════════════════════════ */}
          <div className={`${styles.phaseContainer} ${phase === 4 ? styles.phaseVisible : ""}`}>
            <div className={styles.card}>
              <div className={styles.completionCard}>
                <div className={styles.compIcon}>✅</div>
                <div className={styles.compTitle}>导入成功</div>
                <div className={styles.compSubtitle}>
                  已导入 {data.totalChapters} 章小说内容，系统已完成四库分析和动态层提取。
                  <br />
                  你可以直接进入创作工作台，继续后续的写作。
                </div>
                <div className={styles.compStats}>
                  <div className={styles.compStat}>
                    <div className={styles.compStatValue}>{data.totalChapters}</div>
                    <div className={styles.compStatLabel}>已导入章节</div>
                  </div>
                  <div className={styles.compStat}>
                    <div className={styles.compStatValue}>{data.characters}</div>
                    <div className={styles.compStatLabel}>提取人物</div>
                  </div>
                  <div className={styles.compStat}>
                    <div className={styles.compStatValue}>{data.timeline}</div>
                    <div className={styles.compStatLabel}>时间线节点</div>
                  </div>
                  <div className={styles.compStat}>
                    <div className={styles.compStatValue}>{data.commitments}</div>
                    <div className={styles.compStatLabel}>剧情承诺</div>
                  </div>
                  <div className={styles.compStat}>
                    <div className={styles.compStatValue}>{data.world}</div>
                    <div className={styles.compStatLabel}>世界观条目</div>
                  </div>
                </div>
                <div className={styles.compActions}>
                  <button className={styles.btnSecondary} onClick={goBack}>
                    ← 返回作品列表
                  </button>
                  <button className={styles.btnAmber} onClick={goToWorkspace}>
                    进入创作工作台 →
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* ╔═══════════════════════════════════════════════════════╗
           ║  MOBILE SHELL                                         ║
           ╚═══════════════════════════════════════════════════════╝ */}
      <div className={styles.mobileShell}>
        {/* ── Status Bar ── */}
        <div className={styles.mStatusBar}>
          <span className={styles.mStatusTime}>9:41</span>
          <div className={styles.mStatusIcons}>
            <svg viewBox="0 0 24 24">
              <path d="M1 9l2 2c4.97-4.97 13.03-4.97 18 0l2-2C16.93 2.93 7.08 2.93 1 9zm8 8l3 3 3-3c-1.65-1.66-4.34-1.66-6 0zm-4-4l2 2c2.76-2.76 7.24-2.76 10 0l2-2C15.14 9.14 8.87 9.14 5 13z" />
            </svg>
            <svg viewBox="0 0 24 24">
              <path d="M15.67 4H14V2h-4v2H8.33C7.6 4 7 4.6 7 5.33v15.33C7 21.4 7.6 22 8.33 22h7.33c.74 0 1.34-.6 1.34-1.33V5.33C17 4.6 16.4 4 15.67 4z" />
            </svg>
          </div>
        </div>

        {/* ── Top Nav ── */}
        <div className={styles.mTopNav}>
          <button className={styles.mBackBtn} onClick={goBack}>
            ←
          </button>
          <span className={styles.mNavTitle}>导入已有小说</span>
        </div>

        {/* ── Step Bar ── */}
        <div className={styles.mStepBar}>
          {[0, 1, 2, 3].map((stepIdx) => (
            <div
              key={stepIdx}
              className={`${styles.mStepItem} ${
                phase > stepIdx || phase === 4 ? styles.mStepDone : phase === stepIdx ? styles.mStepActive : ""
              }`}
            >
              <div className={styles.mStepDot}>{stepIdx + 1}</div>
              <span className={styles.mStepLabel}>{getPhaseLabel(stepIdx)}</span>
              <div className={styles.mStepLine} />
            </div>
          ))}
        </div>

        {/* ── Main Content ── */}
        <div className={styles.mMainContent}>
          {/* Phase 0 */}
          <div className={`${styles.mPhase} ${phase === 0 ? styles.mPhaseVisible : ""}`}>
            <div className={styles.mImportOptions}>
              <div
                className={`${styles.mOption} ${importMethod === "paste" ? styles.mOptionSelected : ""}`}
                onClick={() => setImportMethod("paste")}
              >
                <div className={styles.mOptIcon}>📝</div>
                <div className={styles.mOptTitle}>粘贴文本</div>
                <div className={styles.mOptDesc}>粘贴章节正文，系统自动识别章节结构</div>
              </div>
              <div className={`${styles.mPasteArea} ${importMethod === "paste" ? styles.mPasteShow : ""}`}>
                <textarea
                  placeholder="在此粘贴小说文本…"
                  value={pasteText}
                  onChange={(e) => setPasteText(e.target.value)}
                />
                <div className={styles.mPasteHint}>
                  <span>{charCount} 字</span>
                </div>
              </div>

              <div
                className={`${styles.mOption} ${importMethod === "file" ? styles.mOptionSelected : ""}`}
                onClick={() => setImportMethod("file")}
              >
                <div className={styles.mOptIcon}>📁</div>
                <div className={styles.mOptTitle}>上传文件</div>
                <div className={styles.mOptDesc}>支持 .txt / .docx 格式</div>
              </div>
              <div className={`${styles.mUploadZone} ${importMethod === "file" ? styles.mUploadShow : ""}`}>
                <div className={styles.mUploadDrop} onClick={() => mFileInputRef.current?.click()}>
                  点击选择文件或拖拽至此
                  <br />
                  <span style={{ fontSize: 12, color: "var(--color-text-tertiary)" }}>支持 .txt, .docx</span>
                </div>
                <input
                  ref={mFileInputRef}
                  type="file"
                  accept=".txt,.docx"
                  style={{ display: "none" }}
                  onChange={onFileInputChange}
                />
                {uploadFile && (
                  <div className={`${styles.mUploadInfo} ${styles.mUploadShowInfo}`}>
                    <span>📄</span>
                    <span>{uploadFile.name}</span>
                  </div>
                )}
              </div>
            </div>
            <button
              className={`${styles.mBigBtn} ${styles.mBigBtnBrand}`}
              disabled={importMethod === null}
              onClick={mStartAnalysis}
            >
              开始分析
            </button>
          </div>

          {/* Phase 1 */}
          <div className={`${styles.mPhase} ${phase === 1 ? styles.mPhaseVisible : ""}`}>
            <div className={styles.mAnalysisList}>
              {progressItems.map((item) => (
                <div
                  key={item.id}
                  className={`${styles.mAnalysisItem} ${
                    item.status === "done"
                      ? styles.mAnalysisDone
                      : item.status === "active"
                      ? styles.mAnalysisRunning
                      : ""
                  }`}
                >
                  <div className={styles.mAnalysisIcon}>{item.status === "done" ? "✅" : item.icon}</div>
                  <span className={styles.mAnalysisText}>
                    {item.status === "done" ? `${item.label}提取完成` : `${item.label}提取中...`}
                  </span>
                  <span className={styles.mAnalysisStatus}>
                    {item.status === "active" ? (
                      <div className={styles.mSpinner} />
                    ) : item.status === "done" ? (
                      "✓"
                    ) : (
                      "等待"
                    )}
                  </span>
                </div>
              ))}
            </div>
            <div className={styles.mProgressTrack}>
              <div className={styles.mProgressFill} style={{ width: `${pct}%` }} />
            </div>
            <div className={styles.mProgressLabel}>分析进度：{overallDone}/4</div>
          </div>

          {/* Phase 2 */}
          <div className={`${styles.mPhase} ${phase === 2 ? styles.mPhaseVisible : ""}`}>
            <div className={styles.mPhase2Title}>近三章动态分析（第21-23章）</div>
            <div className={styles.mChapterCards}>
              {data.chapters.map((ch) => (
                <div key={ch.number} className={styles.mChapterCard}>
                  <div className={styles.mChNum}>第{ch.number}章</div>
                  <div className={styles.mChTitle}>{ch.title}</div>
                  <div className={styles.mChSummary}>{ch.events[0]}</div>
                </div>
              ))}
            </div>
            <div className={styles.mInsights}>
              <div className={styles.mInsightRow}>
                <span className={styles.mInsightIcon}>👤</span>
                <span className={styles.mInsightLabel}>POV</span>
                <span className={styles.mInsightValue}>{data.dynamicLayer.pov}</span>
              </div>
              <div className={styles.mInsightRow}>
                <span className={styles.mInsightIcon}>📍</span>
                <span className={styles.mInsightLabel}>地点</span>
                <span className={styles.mInsightValue}>{data.dynamicLayer.location}</span>
              </div>
              <div className={styles.mInsightRow}>
                <span className={styles.mInsightIcon}>⚡</span>
                <span className={styles.mInsightLabel}>活跃钩子</span>
                <span className={`${styles.mInsightValue} ${styles.mInsightWarn}`}>
                  {data.dynamicLayer.hooks.join(" · ")}
                </span>
              </div>
              <div className={styles.mInsightRow}>
                <span className={styles.mInsightIcon}>✅</span>
                <span className={styles.mInsightLabel}>连贯性</span>
                <span className={`${styles.mInsightValue} ${styles.mInsightGood}`}>良好</span>
              </div>
            </div>
          </div>

          {/* Phase 3 */}
          <div className={`${styles.mPhase} ${phase === 3 ? styles.mPhaseVisible : ""}`}>
            <div className={styles.mSummaryCard}>
              <div className={styles.mSummaryHeader}>📊 四库摘要</div>
              <div className={styles.mSummaryGrid}>
                <div className={styles.mSummaryItem}>
                  <div className={styles.mSiValue}>{data.characters}</div>
                  <div className={styles.mSiLabel}>人物</div>
                </div>
                <div className={styles.mSummaryItem}>
                  <div className={styles.mSiValue}>{data.timeline}</div>
                  <div className={styles.mSiLabel}>时间线节点</div>
                </div>
                <div className={styles.mSummaryItem}>
                  <div className={styles.mSiValue}>{data.commitments}</div>
                  <div className={styles.mSiLabel}>剧情承诺</div>
                </div>
                <div className={styles.mSummaryItem}>
                  <div className={styles.mSiValue}>{data.world}</div>
                  <div className={styles.mSiLabel}>世界观</div>
                </div>
              </div>
            </div>
            <div className={styles.mConflictCard}>
              <div className={styles.mConflictHeader}>⚠️ 冲突标记</div>
              {data.conflicts.map((c, i) => (
                <div key={i} className={styles.mConflictItem}>
                  <div className={styles.mConflictDot} />
                  <div className={styles.mConflictText}>
                    {c.main}
                    <span className={styles.mConflictTag}>{i === 0 ? "时间线矛盾" : "承诺悬置"}</span>
                  </div>
                </div>
              ))}
            </div>
            <button className={`${styles.mBigBtn} ${styles.mBigBtnBrand}`} onClick={mConfirmImport}>
              确认导入
            </button>
            <a className={styles.mGhostLink} onClick={resetAll}>
              放弃
            </a>
          </div>

          {/* Done Page */}
          <div className={`${styles.mDonePage} ${phase === 4 ? styles.mDoneVisible : ""}`}>
            <div className={styles.mDoneCheck}>✓</div>
            <div className={styles.mDoneTitle}>导入完成！</div>
            <div className={styles.mDoneSub}>已导入 {data.totalChapters} 章</div>
            <div className={styles.mDoneStats}>
              {[
                { value: String(data.characters), label: "人物" },
                { value: String(data.timeline), label: "时间线" },
                { value: String(data.commitments), label: "承诺" },
                { value: String(data.world), label: "世界观" },
              ].map((stat, i) => (
                <div key={i} className={styles.mDoneStat}>
                  <div className={styles.mDsValue}>{stat.value}</div>
                  <div className={styles.mDsLabel}>{stat.label}</div>
                </div>
              ))}
            </div>
            <div className={styles.mDoneActions}>
              <button className={`${styles.mBigBtn} ${styles.mBigBtnBrand}`} onClick={goToWorkspace}>
                进入创作工作台 →
              </button>
              <a className={styles.mGhostLink} onClick={goBack}>
                返回作品列表
              </a>
            </div>
          </div>
        </div>

        {/* ── Bottom Nav ── */}
        <div className={styles.mBottomNav}>
          {[
            { icon: <path d="M10 20v-6h4v6h5v-8h3L12 3 2 12h3v8z" />, label: "首页" },
            { icon: <path d="M18 2H6c-1.1 0-2 .9-2 2v16c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zM6 4h5v8l-2.5-1.5L6 12V4z" />, label: "作品" },
            { icon: <path d="M3 17.25V21h3.75L17.81 9.94l-3.75-3.75L3 17.25zM20.71 7.04c.39-.39.39-1.02 0-1.41l-2.34-2.34c-.39-.39-1.02-.39-1.41 0l-1.83 1.83 3.75 3.75 1.83-1.83z" />, label: "创作" },
            { icon: <path d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z" />, label: "我的" },
          ].map((tab, i) => (
            <button key={i} className={`${styles.mNavTab} ${i === 2 ? styles.mNavTabActive : ""}`}>
              <svg viewBox="0 0 24 24">{tab.icon}</svg>
              <span>{tab.label}</span>
            </button>
          ))}
        </div>
      </div>
    </>
  );
}
