"use client";

import { useState, useEffect, useCallback, useMemo } from "react";
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
  const [cardStatusFilter, setCardStatusFilter] = useState<"all" | "active" | "retired">("active");

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

  // 根据退役过滤卡牌
  const filteredCards = useMemo(() => {
    if (cardStatusFilter === "all") return cards;
    if (cardStatusFilter === "retired") return cards.filter((c) => c.status === "retired");
    return cards.filter((c) => c.status !== "retired");
  }, [cards, cardStatusFilter]);

  // 卡牌状态标签映射
  const statusLabelMap: Record<string, string> = {
    available: "可用",
    drawn: "已抽取",
    used: "已使用",
    expired: "已过期",
    retired: "已退役",
  };

  // 判断卡牌是否处于新鲜期
  const isFresh = (card: CardPool): boolean => {
    if (card.status === "retired") return false;
    if (card.freshness_chapter === undefined) return false;
    // 如果 freshness_chapter 大于当前抽取次数，认为仍在新颖
    return card.freshness_chapter > (card.draw_count || 0);
  };

  const activeCardCount = cards.filter((c) => c.status !== "retired").length;
  const retiredCardCount = cards.filter((c) => c.status === "retired").length;

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

      {/* 卡牌状态过滤 */}
      <div className={styles.filterBar}>
        <button
          className={`${styles.filterBtn} ${cardStatusFilter === "active" ? styles.active : ""}`}
          onClick={() => setCardStatusFilter("active")}
        >
          活跃 ({activeCardCount})
        </button>
        <button
          className={`${styles.filterBtn} ${cardStatusFilter === "retired" ? styles.active : ""}`}
          onClick={() => setCardStatusFilter("retired")}
        >
          已退役 ({retiredCardCount})
        </button>
        <button
          className={`${styles.filterBtn} ${cardStatusFilter === "all" ? styles.active : ""}`}
          onClick={() => setCardStatusFilter("all")}
        >
          全部 ({cards.length})
        </button>
      </div>

      {/* 卡牌列表 */}
      <div className={styles.list}>
        <h4 className={styles.panelTitle}>卡牌池 ({filteredCards.length})</h4>
        {filteredCards.length === 0 ? (
          <div className={styles.empty}>
            {cardStatusFilter === "active"
              ? "暂无活跃卡牌"
              : cardStatusFilter === "retired"
                ? "暂无已退役卡牌"
                : "暂无卡牌数据"}
          </div>
        ) : (
          filteredCards.map((card) => (
            <div
              key={card.id}
              className={`${styles.card} ${styles[`rarity_${card.rarity}`]} ${card.status === "retired" ? styles.retired : ""}`}
              onClick={() => card.status !== "retired" && toggleCardSelection(card.id)}
            >
              {card.status === "retired" && (
                <div className={styles.retiredOverlay}>已退役</div>
              )}
              <div className={styles.cardHeader}>
                <span className={styles.cardIcon}>
                  {RARITY_ICONS[card.rarity] || "⚪"}
                </span>
                <span className={styles.cardName}>{card.name}</span>
                <span className={styles.cardRarity}>
                  {RARITY_LABELS[card.rarity] || card.rarity}
                </span>
                {/* 新鲜期指示器 */}
                {isFresh(card) && (
                  <span className={styles.freshBadge} title="此卡牌处于新鲜期">
                    ✨ 新鲜
                  </span>
                )}
              </div>
              <p className={styles.cardDescription}>{card.description}</p>
              <div className={styles.cardFooter}>
                <span className={styles.cardType}>
                  {card.direction_type}
                </span>
                <span className={`${styles.cardStatus} ${card.status === "retired" ? styles.statusRetired : ""}`}>
                  {statusLabelMap[card.status] || card.status}
                </span>
                {card.draw_count !== undefined && (
                  <span className={styles.cardDrawCount}>
                    抽取次数: {card.draw_count}
                  </span>
                )}
              </div>
              {/* 退役原因和退役章节 */}
              {card.status === "retired" && card.retired_reason && (
                <div className={styles.retiredInfo}>
                  <span className={styles.retiredReason}>
                    退役原因: {card.retired_reason}
                  </span>
                  {card.retired_at_chapter && (
                    <span className={styles.retiredChapter}>
                      退役章节: 第{card.retired_at_chapter}章
                    </span>
                  )}
                </div>
              )}
              <div className={styles.cardActions}>
                {card.status !== "retired" && (
                  <button
                    className={styles.retireButton}
                    onClick={(e) => {
                      e.stopPropagation();
                      handleRetire(card.id);
                    }}
                  >
                    停用
                  </button>
                )}
              </div>
              {selectedCards.includes(card.id) && card.status !== "retired" && (
                <div className={styles.selectedBadge}>✓ 已选择</div>
              )}
            </div>
          ))
        )}
      </div>
    </div>
  );
}
