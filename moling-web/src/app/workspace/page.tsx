'use client';

import { useState, useEffect, useRef, useCallback } from 'react';
import styles from './Workspace.module.css';
import {
  getCards,
  generateChapter,
  getGenerationProgress,
  confirmChapter,
  reviseChapter,
  cancelGeneration,
  getHealthAlerts,
  getSuggestions,
} from '@/api';
import type { CardDirection, GenerationProgress } from '@/api';

// 类型定义
interface Character {
  id: string;
  name: string;
  role: 'mc' | 'ally' | 'enemy' | 'neutral';
  status: string;
  emotion: string;
  location: string;
}

interface Commitment {
  id: string;
  type: 'foreshadow' | 'arc' | 'subplot' | 'theme';
  title: string;
  status: string;
  link?: string;
}

interface Suggestion {
  id: string;
  text: string;
}

interface CardDirection {
  id: string;
  rarity: 'common' | 'rare' | 'epic' | 'legendary';
  title: string;
  desc: string;
  tags: string[];
  weight: number;
}

// 角色样式映射
const roleAvatarClass: Record<string, string> = {
  mc: 'charAvatarMc',
  ally: 'charAvatarAlly',
  enemy: 'charAvatarEnemy',
  neutral: 'charAvatarNeutral',
};

const roleBadgeClass: Record<string, string> = {
  mc: 'charBadgeMc',
  ally: 'charBadgeAlly',
  enemy: 'charBadgeEnemy',
  neutral: 'charBadgeNeutral',
};

const typeBadgeClass: Record<string, string> = {
  foreshadow: 'commitmentTypeBadgeForeshadow',
  arc: 'commitmentTypeBadgeArc',
  subplot: 'commitmentTypeBadgeSubplot',
  theme: 'commitmentTypeBadgeTheme',
};

export default function WorkspacePage() {
  // 状态管理
  const [activeTab, setActiveTab] = useState('characters');
  const [leftPanelCollapsed, setLeftPanelCollapsed] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const [draftConfirmed, setDraftConfirmed] = useState(false);
  const [countdown, setCountdown] = useState(6);
  const [generating, setGenerating] = useState(false);
  const [genProgress, setGenProgress] = useState(0);
  const [genResult, setGenResult] = useState<null | { words: number; time: number }>(null);
  const [suggestions, setSuggestions] = useState<Array<{ id: string; text: string }>>([]);
  const [healthAlerts, setHealthAlerts] = useState<Array<{ type: string; message: string; severity: 'info' | 'warning' | 'error' }>>([]);

  // 模拟数据
  const mockCharacters: Character[] = [
    { id: '1', name: '林霄', role: 'mc', status: '赶赴考核', emotion: '紧张', location: '宗门山脚' },
    { id: '2', name: '墨导师', role: 'ally', status: '主持考核', emotion: '平静', location: '演武场' },
    { id: '3', name: '夜无痕', role: 'enemy', status: '暗中观察', emotion: '轻蔑', location: '暗处' },
  ];

  const mockCommitments: Commitment[] = [
    { id: '1', type: 'foreshadow', title: '神秘玉佩', status: '待回收', link: '关联：林霄、苏姨' },
    { id: '2', type: 'arc', title: '林霄·成长', status: '推进中', link: '下一阶段：宗门考核' },
    { id: '3', type: 'subplot', title: '神秘人身份', status: '活跃', link: '关联：墨导师' },
  ];

  const mockSuggestions: Suggestion[] = [
    { id: '1', text: '可以让墨导师在考核规则中暗藏与神秘人话语的呼应，让读者意识到"导师可能知道更多"。' },
    { id: '2', text: '考虑让夜无痕在第一轮中刻意与林霄对峙，展示双方实力差距的同时埋下后续合作伏笔。' },
    { id: '3', text: '玉佩的发热可以和灵力考核规则产生共鸣，暗示玉佩与宗门之间有更深层联系。' },
  ];

  const [cards, setCards] = useState<CardDirection[]>([
    { id: '1', rarity: 'common', title: '主角隐藏实力暗中观察导师', desc: '林霄决定在考核中隐藏真正实力...', tags: ['伏笔推进', '林霄·观察'], weight: 30 },
    { id: '2', rarity: 'rare', title: '导师宣布规则时说了和神秘人一样的话', desc: '墨导师在解释考核规则时...', tags: ['伏笔回收', '导师·异常'], weight: 40 },
    { id: '3', rarity: 'epic', title: '考核突发意外有人偷袭导师', desc: '考核中途，一道黑影突袭墨导师！...', tags: ['伏笔引爆', '第三方入场'], weight: 30 },
  ]);

  const [selectedCards, setSelectedCards] = useState<string[]>(['1', '2']);

  // 倒计时逻辑
  const countdownRef = useRef<number | null>(null);

  useEffect(() => {
    if (!draftConfirmed && countdown > 0) {
      countdownRef.current = window.setInterval(() => {
        setCountdown(prev => {
          if (prev <= 1) {
            confirmDraft();
            return 0;
          }
          return prev - 1;
        });
      }, 1000);
    }

    return () => {
      if (countdownRef.current) clearInterval(countdownRef.current);
    };
  }, [draftConfirmed]);

  const confirmDraft = () => {
    setDraftConfirmed(true);
    if (countdownRef.current) clearInterval(countdownRef.current);
    showToast('草稿已确认');
  };

  const rejectDraft = () => {
    setDraftConfirmed(false);
    setCountdown(6);
    showToast('草稿已拒绝，重新生成...');
  };

  const showToast = (msg: string) => {
    console.log('Toast:', msg);
  };

  const openModal = () => setModalOpen(true);
  const closeModal = () => {
    setModalOpen(false);
    setGenerating(false);
    setGenProgress(0);
    setGenResult(null);
  };

  const toggleCardSelection = (cardId: string) => {
    setSelectedCards(prev =>
      prev.includes(cardId)
        ? prev.filter(id => id !== cardId)
        : [...prev, cardId]
    );
  };

  const generateContent = async () => {
    setGenerating(true);
    setGenProgress(0);

    try {
      // 调用生成 API
      const selectedCardData = cards.filter(c => selectedCards.includes(c.id));
      const response = await generateChapter({
        chapterId: 'current-chapter-id', // TODO: 从 URL 或 context 获取
        cardIds: selectedCardData.map(c => c.id),
        weights: selectedCardData.map(c => c.weight),
        mode: selectedCards.length === 1 ? 'single' : selectedCards.length === 2 ? 'dual' : 'all',
      });

      // 轮询进度
      const pollProgress = async (taskId: string) => {
        const progress: GenerationProgress = await getGenerationProgress(taskId);
        setGenProgress(progress.progress);

        if (progress.status === 'completed' && progress.result) {
          setGenResult({
            words: progress.result.wordCount,
            time: progress.result.timeSpent,
          });
          showToast('✅ 章节生成完成！');
          setGenerating(false);
          return;
        }

        if (progress.status === 'failed') {
          showToast(`❌ 生成失败: ${progress.error || '未知错误'}`);
          setGenerating(false);
          return;
        }

        // 继续轮询
        setTimeout(() => pollProgress(taskId), 1000);
      };

      pollProgress(response.taskId);
    } catch (error) {
      console.error('生成失败:', error);
      showToast(`❌ 生成失败: ${error instanceof Error ? error.message : '未知错误'}`);
      setGenerating(false);
    }
  };

  const confirmInspiration = async () => {
    try {
      await confirmChapter({
        chapterId: 'current-chapter-id', // TODO: 从 URL 或 context 获取
        content: '', // TODO: 获取编辑器内容
      });
      showToast('✅ 已确认收纳');
      closeModal();
    } catch (error) {
      console.error('确认失败:', error);
      showToast(`❌ 确认失败: ${error instanceof Error ? error.message : '未知错误'}`);
    }
  };

  // 加载灵感卡牌
  useEffect(() => {
    const loadCards = async () => {
      try {
        const cardsData = await getCards('current-chapter-id');
        setCards(cardsData);
      } catch (error) {
        console.error('加载卡牌失败:', error);
        // 使用默认卡牌（已在 state 中定义）
      }
    };

    loadCards();
  }, []);

  // 加载建议
  useEffect(() => {
    const loadSuggestions = async () => {
      try {
        const suggestionsData = await getSuggestions('current-chapter-id');
        setSuggestions(suggestionsData);
      } catch (error) {
        console.error('加载建议失败:', error);
        // 使用默认建议（已在 state 中定义）
      }
    };

    loadSuggestions();
  }, []);

  // 轮询健康告警
  useEffect(() => {
    const loadHealthAlerts = async () => {
      try {
        const alerts = await getHealthAlerts('current-project-id');
        setHealthAlerts(alerts);
      } catch (error) {
        console.error('加载健康告警失败:', error);
      }
    };

    loadHealthAlerts();
    const interval = setInterval(loadHealthAlerts, 30000); // 每 30 秒轮询一次

    return () => clearInterval(interval);
  }, []);

  return (
    <div className={styles.appLayout}>
      {/* Header */}
      <header className={styles.appHeader}>
        <button
          className={styles.headerMenuBtn}
          onClick={() => setLeftPanelCollapsed(!leftPanelCollapsed)}
        >
          ☰
        </button>
        <span className={styles.headerBrand}>墨灵</span>
        <span className={styles.headerChapter}>
          第15章·<span>宗门考核</span>
        </span>
        <div style={{ flex: 1 }} />
        <div className={styles.headerSaveStatus}>
          <span className={styles.pulseDot} />
          <span>自动保存中</span>
        </div>
        <button className={styles.headerIconBtn}>🔔</button>
        <div className={styles.headerAvatar}>作</div>
      </header>

      {/* Body */}
      <div className={styles.appBody}>
        {/* Left Panel */}
        <aside
          className={`${styles.leftPanel} ${leftPanelCollapsed ? styles.leftPanelCollapsed : ''}`}
        >
          <div className={styles.panelTabs}>
            {['characters', 'timeline', 'commitments', 'worldview'].map(tab => (
              <button
                key={tab}
                className={`${styles.panelTabBtn} ${activeTab === tab ? styles.panelTabBtnActive : ''}`}
                onClick={() => setActiveTab(tab)}
              >
                {tab === 'characters' && '👥 人物'}
                {tab === 'timeline' && '⏱️ 时间线'}
                {tab === 'commitments' && '📖 剧情承诺'}
                {tab === 'worldview' && '🌍 世界观'}
              </button>
            ))}
          </div>

          <div className={styles.panelContentWrap}>
            {/* 人物库 */}
            <div className={`${styles.panelContent} ${activeTab === 'characters' ? styles.panelContentActive : ''}`}>
              {mockCharacters.map(char => (
                <div key={char.id} className={styles.characterCard}>
                  <div className={styles.charHeader}>
                    <div className={`${styles.charAvatar} ${styles[roleAvatarClass[char.role]]}`}>
                      {char.name[0]}
                    </div>
                    <div>
                      <div className={styles.charName}>{char.name}</div>
                      <span className={`${styles.charBadge} ${styles[roleBadgeClass[char.role]]}`}>
                        {char.role === 'mc' ? '主角' : char.role === 'ally' ? '盟友' : char.role === 'enemy' ? '对手' : '中立'}
                      </span>
                    </div>
                  </div>
                  <div className={styles.charStatus}>
                    <div>状态：{char.status}</div>
                    <div>情绪：{char.emotion}</div>
                    <div>位置：{char.location}</div>
                  </div>
                </div>
              ))}
            </div>

            {/* 剧情承诺 */}
            <div className={`${styles.panelContent} ${activeTab === 'commitments' ? styles.panelContentActive : ''}`}>
              {mockCommitments.map(item => (
                <div key={item.id} className={styles.commitmentItem}>
                  <span className={`${styles.commitmentTypeBadge} ${styles[typeBadgeClass[item.type]]}`}>
                    {item.type === 'foreshadow' ? '伏笔' : item.type === 'arc' ? '弧线' : item.type === 'subplot' ? '支线' : '主题'}
                  </span>
                  <div className={styles.commitmentTitle}>{item.title}</div>
                  <div className={styles.commitmentStatus}>
                    <span>{item.status}</span>
                  </div>
                  {item.link && <div className={styles.commitmentLink}>→ {item.link}</div>}
                </div>
              ))}
            </div>
          </div>
        </aside>

        {/* Center Panel (Editor) */}
        <main className={styles.centerPanel}>
          <div className={styles.editorScroll}>
            {/* 健康告警 */}
            {healthAlerts.length > 0 && (
              <div style={{ marginBottom: 16 }}>
                {healthAlerts.map((alert, index) => (
                  <div
                    key={index}
                    style={{
                      padding: '8px 12px',
                      marginBottom: 8,
                      borderRadius: 8,
                      fontSize: 13,
                      background: alert.severity === 'error' ? 'rgba(239,68,68,0.1)' : alert.severity === 'warning' ? 'rgba(251,191,36,0.1)' : 'rgba(99,102,241,0.1)',
                      border: `1px solid ${alert.severity === 'error' ? 'rgba(239,68,68,0.2)' : alert.severity === 'warning' ? 'rgba(251,191,36,0.2)' : 'rgba(99,102,241,0.2)'}`,
                      color: alert.severity === 'error' ? '#ef4444' : alert.severity === 'warning' ? '#fbbf24' : '#6366f1',
                    }}
                  >
                    {alert.severity === 'error' ? '⚠️' : alert.severity === 'warning' ? '⚡' : 'ℹ️'} {alert.message}
                  </div>
                ))}
              </div>
            )}

            <div className={styles.editorChapterLabel}>第十五章</div>
            <div className={styles.editorChapterTitle}>宗门<span>考核</span></div>
            <div className={styles.editorOutline}>
              大纲：林霄参加宗门考核 → 第一轮对敌 → 发现考官异常 → 暗中试探
            </div>

            {/* 前情摘要 */}
            <div className={styles.contextCard}>
              <div className={styles.contextCardHeader}>
                <div className={styles.contextCardLabel}>📋 前情回顾 · 自动摘要</div>
                <button className={styles.contextToggle}>收起 ▲</button>
              </div>
              <div className={styles.contextPrevChapter}>第14章 · 暗夜密谈</div>
              <div className={styles.contextText}>
                主角在考核前夜无法入睡，在院中遇到一个披着斗篷的神秘人...
              </div>
            </div>

            {/* 编辑器主体 */}
            <div className={styles.editorBody} contentEditable>
              <p>晨曦初露，演武场上已经聚集了数十名弟子...</p>
              {!draftConfirmed && (
                <p className={styles.draftText} id="draftParagraph">
                  墨导师今日的举止似乎与往常不同...
                </p>
              )}
            </div>

            {/* 倒计时 */}
            {!draftConfirmed && (
              <div className={styles.draftCountdown}>
                <div className={styles.draftCountdownBar}>
                  <div
                    className={styles.draftCountdownFill}
                    style={{ width: `${(countdown / 6) * 100}%` }}
                  />
                </div>
                <span className={styles.draftCountdownText}>{countdown}秒后自动确认</span>
              </div>
            )}
          </div>

          {/* Bottom Toolbar */}
          <div className={styles.editorToolbar}>
            <div className={styles.toolbarInputRow}>
              <input
                className={styles.toolbarInput}
                placeholder="📝 有想法？在这里说..."
              />
              <div className={styles.toolbarActions}>
                <button className={styles.btnDraw} onClick={openModal}>
                  🃏 抽卡
                </button>
                <button className={styles.btnConfirm} onClick={confirmDraft}>
                  ✓ 确认
                </button>
                <button className={styles.btnReject} onClick={rejectDraft}>
                  ✗ 拒绝
                </button>
              </div>
            </div>
          </div>
        </main>

        {/* Right Panel (Agent) */}
        <aside className={styles.rightPanel}>
          <div className={styles.agentStatus}>
            <div className={styles.agentAvatarWrap}>
              <div className={styles.agentAvatar}>🤖</div>
              <div className={styles.agentPulseRing} />
            </div>
            <div>
              <div className={styles.agentName}>墨灵 Agent</div>
              <div className={styles.agentState}>自动推进中...</div>
            </div>
          </div>

          <div className={styles.agentSection}>
            <div className={styles.agentSectionTitle}>💡 建议</div>
            {suggestions.map(suggestion => (
              <div key={suggestion.id} className={styles.suggestionCard}>
                <div className={styles.suggestionText}>{suggestion.text}</div>
                <button className={styles.suggestionAdopt}>采纳</button>
              </div>
            ))}
          </div>

          <div className={styles.drawCta}>
            <button className={styles.drawCtaBtn} onClick={openModal}>
              🃏 抽章节灵感卡
            </button>
          </div>
        </aside>
      </div>

      {/* Card Draw Modal */}
      {modalOpen && (
        <div className={styles.modalOverlay} onClick={(e) => e.target === e.currentTarget && closeModal()}>
          <div className={styles.modalCard}>
            <div className={styles.modalHeader}>
              <div className={styles.modalTitle}>🎴 章节灵感卡 · 第15章·宗门考核</div>
              <div className={styles.modalSubtitle}>选择卡片 → 调节偏好 → 生成章节</div>
            </div>

            <div className={styles.modalCards}>
              {cards.map(card => (
                <div
                  key={card.id}
                  className={`${styles.inspirationCard} ${styles[`inspirationCard${card.rarity.charAt(0).toUpperCase() + card.rarity.slice(1)}`]} ${selectedCards.includes(card.id) ? styles.inspirationCardSelected : ''}`}
                  onClick={() => toggleCardSelection(card.id)}
                >
                  <div className={styles.cardRarity}>
                    {card.rarity === 'common' ? '⚪' : card.rarity === 'rare' ? '🔵' : card.rarity === 'epic' ? '🟣' : '🟡'}
                  </div>
                  <div className={`${styles.cardRarityLabel} ${styles[`cardRarityLabel${card.rarity.charAt(0).toUpperCase() + card.rarity.slice(1)}`]}`}>
                    {card.rarity === 'common' ? '稳妥方向' : card.rarity === 'rare' ? '有趣方向' : card.rarity === 'epic' ? '惊艳方向' : '传奇方向'}
                  </div>
                  <div className={styles.cardDirectionTitle}>{card.title}</div>
                  <div className={styles.cardDirectionDesc}>{card.desc}</div>
                  <div className={styles.cardTags}>
                    {card.tags.map((tag, i) => (
                      <span key={i} className={styles.cardTag}>{tag}</span>
                    ))}
                  </div>
                  <input
                    type="range"
                    className={styles.weightSlider}
                    min="0"
                    max="100"
                    value={card.weight}
                    onChange={(e) => {
                      const newCards = cards.map(c =>
                        c.id === card.id ? { ...c, weight: parseInt(e.target.value) } : c
                      );
                      setCards(newCards);
                    }}
                    onClick={(e) => e.stopPropagation()}
                  />
                  <span className={styles.weightValue}>{card.weight}%</span>
                </div>
              ))}
            </div>

            {/* 生成按钮区 */}
            <div className={styles.modalFooter}>
              <button className={styles.modalBtnSecondary} onClick={closeModal}>
                关闭
              </button>
              <button className={styles.modalBtnPrimary} onClick={generateContent} disabled={generating}>
                {generating ? '生成中...' : '🚀 AI生文'}
              </button>
            </div>

            {/* 生成进度 */}
            {generating && (
              <div className={styles.genProgress}>
                <div className={styles.genProgressTitle}>⏳ 生成中...</div>
                <div className={styles.genProgressBar}>
                  <div className={styles.genProgressFill} style={{ width: `${genProgress}%` }} />
                </div>
              </div>
            )}

            {/* 生成结果 */}
            {genResult && (
              <div className={styles.genResult}>
                <div className={styles.genResultHeader}>✅ 章节生成完成</div>
                <div className={styles.genResultStats}>
                  <span>📏 ~{genResult.words}字</span>
                  <span>⏱️ {genResult.time}s</span>
                </div>
                <div className={styles.genResultActions}>
                  <button className={styles.modalBtnPrimary} onClick={confirmInspiration}>
                    应用到正文
                  </button>
                  <button className={styles.modalBtnSecondary} onClick={() => setGenResult(null)}>
                    重新生成
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
