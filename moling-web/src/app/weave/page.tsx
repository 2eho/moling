'use client';

import { useState } from 'react';
import styles from './Weave.module.css';

export default function WeavePage() {
  const [selectedMode, setSelectedMode] = useState<string>('balanced');
  const [weaving, setWeaving] = useState(false);
  const [result, setResult] = useState<null | {
    chaptersGenerated: number;
    themesDetected: string[];
    suggestions: string[];
  }>(null);

  const modes = [
    {
      id: 'conservative',
      name: '保守编织',
      desc: '保持原有风格，仅在必要时调整',
      icon: '🛡️',
    },
    {
      id: 'balanced',
      name: '平衡编织',
      desc: '平衡创新与连贯性，推荐选项',
      icon: '⚖️',
    },
    {
      id: 'creative',
      name: '创意编织',
      desc: '大胆创新，提供更多意外发展',
      icon: '🎨',
    },
    {
      id: 'experimental',
      name: '实验编织',
      desc: '突破常规，生成最意外的剧情',
      icon: '🔬',
    },
  ];

  const handleWeave = async () => {
    setWeaving(true);
    setResult(null);

    // Mock API call
    await new Promise(resolve => setTimeout(resolve, 3000));

    setResult({
      chaptersGenerated: 3,
      themesDetected: ['成长', '背叛与信任', '力量觉醒'],
      suggestions: [
        '建议在章节 18 引入新角色以丰富剧情',
        '当前伏笔回收率较低，建议增加回收线索',
        '角色关系网可以在章节 20 时进行一次大调整',
      ],
    });
    setWeaving(false);
  };

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <h1 className={styles.title}>编织模式</h1>
        <p className={styles.subtitle}>
          选择编织策略，AI 将以此为基础生成后续章节
        </p>
      </div>

      <div className={styles.content}>
        {/* Mode Selection */}
        <div className={styles.modes}>
          <h2 className={styles.sectionTitle}>选择编织模式</h2>
          <div className={styles.modeGrid}>
            {modes.map(mode => (
              <div
                key={mode.id}
                className={`${styles.modeCard} ${selectedMode === mode.id ? styles.modeCardSelected : ''}`}
                onClick={() => setSelectedMode(mode.id)}
              >
                <div className={styles.modeIcon}>{mode.icon}</div>
                <h3 className={styles.modeName}>{mode.name}</h3>
                <p className={styles.modeDesc}>{mode.desc}</p>
              </div>
            ))}
          </div>
        </div>

        {/* Weave Button */}
        <div className={styles.action}>
          <button
            className={styles.weaveBtn}
            onClick={handleWeave}
            disabled={weaving}
          >
            {weaving ? '编织中...' : '🧵 开始编织'}
          </button>
        </div>

        {/* Progress */}
        {weaving && (
          <div className={styles.progress}>
            <div className={styles.progressBar}>
              <div className={styles.progressFill} />
            </div>
            <p className={styles.progressText}>正在分析故事结构...</p>
          </div>
        )}

        {/* Result */}
        {result && (
          <div className={styles.result}>
            <h2 className={styles.sectionTitle}>编织结果</h2>

            <div className={styles.resultStats}>
              <div className={styles.stat}>
                <span className={styles.statLabel}>生成章节</span>
                <span className={styles.statValue}>{result.chaptersGenerated}</span>
              </div>
              <div className={styles.stat}>
                <span className={styles.statLabel}>识别主题</span>
                <span className={styles.statValue}>{result.themesDetected.length}</span>
              </div>
            </div>

            <div className={styles.themes}>
              <h3>识别主题</h3>
              <div className={styles.themeTags}>
                {result.themesDetected.map((theme, i) => (
                  <span key={i} className={styles.themeTag}>{theme}</span>
                ))}
              </div>
            </div>

            <div className={styles.suggestions}>
              <h3>AI 建议</h3>
              {result.suggestions.map((suggestion, i) => (
                <div key={i} className={styles.suggestionCard}>
                  <span className={styles.suggestionIcon}>💡</span>
                  <p>{suggestion}</p>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
