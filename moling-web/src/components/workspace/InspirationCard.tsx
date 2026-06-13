"use client";

import styles from "./InspirationCard.module.css";
import { RARITY_LABELS, RARITY_ICONS } from "@/lib/constants";
import type { CardPool } from "@/lib/types";
import { CardRarityBadge } from "@/components/cards/CardRarityBadge";

interface InspirationCardProps {
  card: CardPool;
  selected: boolean;
  onToggle: () => void;
}

const rarityBorderColors: Record<string, string> = {
  common: "var(--color-rarity-common)",
  rare: "var(--color-rarity-rare)",
  epic: "var(--color-rarity-epic)",
  legendary: "var(--color-rarity-legendary)",
};

export function InspirationCard({ card, selected, onToggle }: InspirationCardProps) {
  const borderColor = rarityBorderColors[card.rarity] ?? "var(--color-border-default)";

  return (
    <div
      className={`${styles.card} ${selected ? styles.selected : ""}`}
      style={{ borderColor: selected ? borderColor : undefined }}
      onClick={onToggle}
    >
      <div className={styles.header}>
        <span className={styles.name}>{card.name}</span>
        <CardRarityBadge rarity={card.rarity} />
      </div>
      <span className={styles.rarityLabel}>
        {RARITY_ICONS[card.rarity]} {RARITY_LABELS[card.rarity]}
      </span>
      <p className={styles.description}>{card.description}</p>
      <p className={styles.direction}>{card.direction_text}</p>
      {card.freshness_chapter && (
        <span className={styles.source}>📌 第{card.freshness_chapter}章 · 收纳生成</span>
      )}
    </div>
  );
}
