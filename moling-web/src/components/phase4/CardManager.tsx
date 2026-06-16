"use client";

import { useState, useEffect, useCallback } from "react";
import { cardApi } from "@/lib/api";
import type { CardPool, DrawRecord, Rarity } from "@/lib/types";
import { RARITY_LABELS, RARITY_ICONS } from "@/lib/constants";
import styles from "./CardManager.module.css";

interface CardManagerProps {
  projectId: string;
  chapterId?: string;
}

export function CardManager({ projectId, chapterId }: CardManagerProps) {
  const [cards, setCards] = useState<CardPool[]>([]);
  const [drawResult, setDrawResult] = useState<DrawRecord | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [drawCount, setDrawCount] = useState(3);
  const [mode, setMode] = useState<"normal" | "double" | "guaranteed">("normal");
  const [selectedCards, setSelectedCards] = useState<string[]>([]);
  const [showCreateForm, setShowCreateForm] = useState(false);

  // 创建卡牌表单
  const [formData, setFormData] = useState({
    name: "",
    type: "plot",
    rarity: "common" as Rarity,
    description: "",
  });

  const loadCards = useCallback(async () => {
    try {
      setLoading(true);
      const res = await cardApi.getPool(projectId, 50);
      setCards(Array.isArray(res.data) ? res.data : []);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "加载卡牌失败");
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    if (projectId) {
      loadCards();
    }
  }, [projectId, loadCards]);

  const handleDraw = async () => {
    if (!chapterId) {
      setError("请先选择章节");
      return;
    }
    try {
      setError(null);
      const res = await cardApi.drawCards(projectId, {
        chapter_id: chapterId,
        draw_count: drawCount,
        mode,
        keep_card_ids: selectedCards,
      });
      setDrawResult(res.data || null);
      loadCards(); // 重新加载卡牌池
    } catch (err) {
      setError(err instanceof Error ? err.message : "抽卡失败");
    }
  };

  const handleRedraw = async () => {
    if (!chapterId) {
      setError("请先选择章节");
      return;
    }
    try {
      setError(null);
      const res = await cardApi.redraw(projectId, chapterId, {
        keep_card_ids: selectedCards,
        draw_count: drawCount,
      });
      setDrawResult(res.data || null);
      loadCards();
    } catch (err) {
      setError(err instanceof Error ? err.message : "重抽失败");
    }
  };

  const handleCreateCard = async () => {
    try {
      await cardApi.create(projectId, formData);
      setShowCreateForm(false);
      setFormData({ name: "", type: "plot", rarity: "common", description: "" });
      loadCards();
    } catch (err) {
      setError(err instanceof Error ? err.message : "创建卡牌失败");
    }
  };

  const handleRetire = async (cardId: string) => {
    if (!confirm("确定要停用这张卡牌吗？")) return;
    try {
      await cardApi.retire(projectId, cardId);
      loadCards();
    } catch (err) {
      setError(err instanceof Error ? err.message : "停用卡牌失败");
    }
  };

  const toggleCardSelection = (cardId: string) => {
    if (selectedCards.includes(cardId)) {
      setSelectedCards(selectedCards.filter((id) => id !== cardId));
    } else {
      setSelectedCards([...selectedCards, cardId]);
    }
  };

  if (loading) {
    return <div className={styles.loading}>加载中...</div>;
  }

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <h3 className={styles.title}>卡牌管理</h3>
        <button
          className={styles.createButton}
          onClick={() => setShowCreateForm(true)}
        >
          + 创建卡牌
        </button>
      </div>

      {error && <div className={styles.error}>{error}</div>}

      {/* 抽卡控制面板 */}
      <div className={styles.drawPanel}>
        <h4 className={styles.panelTitle}>抽卡</h4>
        <div className={styles.drawControls}>
          <label className={styles.controlLabel}>
            抽卡数量
            <input
              type="number"
              min={1}
              max={10}
              value={drawCount}
              onChange={(e) => setDrawCount(parseInt(e.target.value) || 3)}
              className={styles.numberInput}
            />
          </label>

          <label className={styles.controlLabel}>
            模式
            <select
              value={mode}
              onChange={(e) => setMode(e.target.value as "normal" | "double" | "guaranteed")}
              className={styles.select}
            >
              <option value="normal">单线</option>
              <option value="double">双线</option>
              <option value="guaranteed">保底</option>
            </select>
          </label>

          <div className={styles.drawButtons}>
            <button
              className={styles.drawButton}
              onClick={handleDraw}
              disabled={!chapterId}
            >
              抽取新卡
            </button>
            <button
              className={styles.redrawButton}
              onClick={handleRedraw}
              disabled={!chapterId}
            >
              重新抽取
            </button>
          </div>
        </div>
      </div>

      {/* 创建卡牌表单 */}
      {showCreateForm && (
        <div className={styles.formOverlay}>
          <div className={styles.form}>
            <h4>创建新卡牌</h4>

            <label className={styles.label}>
              名称
              <input
                type="text"
                value={formData.name}
                onChange={(e) =>
                  setFormData({ ...formData, name: e.target.value })
                }
                className={styles.input}
              />
            </label>

            <label className={styles.label}>
              类型
              <select
                value={formData.type}
                onChange={(e) =>
                  setFormData({ ...formData, type: e.target.value })
                }
                className={styles.select}
              >
                <option value="plot">剧情</option>
                <option value="character">角色</option>
                <option value="worldview">世界观</option>
                <option value="style">风格</option>
                <option value="conflict">冲突</option>
              </select>
            </label>

            <label className={styles.label}>
              稀有度
              <select
                value={formData.rarity}
                onChange={(e) =>
                  setFormData({
                    ...formData,
                    rarity: e.target.value as Rarity,
                  })
                }
                className={styles.select}
              >
                <option value="common">普通</option>
                <option value="rare">稀有</option>
                <option value="epic">史诗</option>
                <option value="legendary">传说</option>
              </select>
            </label>

            <label className={styles.label}>
              描述
              <textarea
                value={formData.description}
                onChange={(e) =>
                  setFormData({ ...formData, description: e.target.value })
                }
                className={styles.textarea}
                rows={3}
              />
            </label>

            <div className={styles.formActions}>
              <button
                className={styles.cancelButton}
                onClick={() => setShowCreateForm(false)}
              >
                取消
              </button>
              <button
                className={styles.submitButton}
                onClick={handleCreateCard}
              >
                创建
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 抽卡结果 */}
      {drawResult && (
        <div className={styles.drawResult}>
          <h4 className={styles.panelTitle}>
            抽卡结果 - 第{drawResult.draw_round}轮
          </h4>
          <p className={styles.remainingRedraws}>
            剩余重抽次数: {drawResult.remaining_redraws}
          </p>
        </div>
      )}

      {/* 卡牌列表 */}
      <div className={styles.list}>
        <h4 className={styles.panelTitle}>卡牌池 ({cards.length})</h4>
        {cards.length === 0 ? (
          <div className={styles.empty}>暂无卡牌数据</div>
        ) : (
          cards.map((card) => (
            <div
              key={card.id}
              className={`${styles.card} ${styles[`rarity_${card.rarity}`]}`}
              onClick={() => toggleCardSelection(card.id)}
            >
              <div className={styles.cardHeader}>
                <span className={styles.cardIcon}>
                  {RARITY_ICONS[card.rarity] || "⚪"}
                </span>
                <span className={styles.cardName}>{card.name}</span>
                <span className={styles.cardRarity}>
                  {RARITY_LABELS[card.rarity] || card.rarity}
                </span>
              </div>
              <p className={styles.cardDescription}>{card.description}</p>
              <div className={styles.cardFooter}>
                <span className={styles.cardType}>
                  {card.direction_type}
                </span>
                <span className={styles.cardStatus}>
                  {card.status === "available"
                    ? "可用"
                    : card.status === "drawn"
                      ? "已抽取"
                      : card.status === "used"
                        ? "已使用"
                        : "已过期"}
                </span>
                {card.draw_count !== undefined && (
                  <span className={styles.cardDrawCount}>
                    抽取次数: {card.draw_count}
                  </span>
                )}
              </div>
              <div className={styles.cardActions}>
                <button
                  className={styles.retireButton}
                  onClick={(e) => {
                    e.stopPropagation();
                    handleRetire(card.id);
                  }}
                >
                  停用
                </button>
              </div>
              {selectedCards.includes(card.id) && (
                <div className={styles.selectedBadge}>✓ 已选择</div>
              )}
            </div>
          ))
        )}
      </div>
    </div>
  );
}
