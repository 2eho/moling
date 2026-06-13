"use client";

import { useState } from "react";
import { Modal } from "@/components/ui/Modal";
import { Button } from "@/components/ui/Button";
import { InspirationCard } from "./InspirationCard";
import { WeightSlider } from "./WeightSlider";
import styles from "./CardModal.module.css";
import { FRESH_CARD_LABEL, DRAW_MODE_OPTIONS, MAX_REDRAW_COUNT } from "@/lib/constants";
import type { CardPool } from "@/lib/types";

interface CardModalProps {
  isOpen: boolean;
  onClose: () => void;
  cards: CardPool[];
  remainingRedraws: number;
  onDraw: (cardIds: string[], weights: number[], mode: string) => void;
  onRedraw: () => void;
  onConfirm: (cardIds: string[], weights: number[], mode: string) => void;
}

export function CardModal({
  isOpen,
  onClose,
  cards,
  remainingRedraws,
  onDraw,
  onRedraw,
  onConfirm,
}: CardModalProps) {
  const [weights, setWeights] = useState<Record<string, number>>({});
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [mode, setMode] = useState("normal");

  const handleWeightChange = (cardId: string, value: number) => {
    setWeights((prev) => ({ ...prev, [cardId]: value }));
  };

  const handleToggleCard = (cardId: string) => {
    setSelectedIds((prev) =>
      prev.includes(cardId)
        ? prev.filter((id) => id !== cardId)
        : [...prev, cardId],
    );
  };

  const handleDraw = () => {
    onDraw(selectedIds, selectedIds.map((id) => weights[id] ?? 50), mode);
  };

  const handleRedraw = () => {
    onRedraw();
  };

  const handleConfirm = () => {
    onConfirm(selectedIds, selectedIds.map((id) => weights[id] ?? 50), mode);
  };

  const displayCards = cards.slice(0, 3);

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="抽取灵感卡"
      footer={
        <div className={styles.footer}>
          <Button variant="secondary" onClick={handleDraw}>
            抽卡
          </Button>
          {remainingRedraws > 0 && (
            <Button variant="ghost" onClick={handleRedraw}>
              🔄 今日可重抽 {remainingRedraws}/{MAX_REDRAW_COUNT} 次
            </Button>
          )}
          <Button
            variant="primary"
            onClick={handleConfirm}
            disabled={selectedIds.length === 0}
          >
            确定选择
          </Button>
        </div>
      }
    >
      <div className={styles.content}>
        <p className={styles.hint}>{FRESH_CARD_LABEL}</p>

        <div className={styles.cardGrid}>
          {displayCards.map((card) => (
            <div key={card.id} className={styles.cardWrapper}>
              <InspirationCard
                card={card}
                selected={selectedIds.includes(card.id)}
                onToggle={() => handleToggleCard(card.id)}
              />
              <WeightSlider
                value={weights[card.id] ?? 50}
                onChange={(v) => handleWeightChange(card.id, v)}
              />
            </div>
          ))}
        </div>

        <div className={styles.modeSection}>
          <label className={styles.modeLabel}>编织模式</label>
          <div className={styles.modeOptions}>
            {DRAW_MODE_OPTIONS.map((opt) => (
              <button
                key={opt.value}
                className={`${styles.modeBtn} ${mode === opt.value ? styles.modeActive : ""}`}
                onClick={() => setMode(opt.value)}
              >
                {opt.label}
              </button>
            ))}
          </div>
        </div>
      </div>
    </Modal>
  );
}
