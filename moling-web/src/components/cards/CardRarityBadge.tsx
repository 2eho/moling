"use client";

import styles from "./CardRarityBadge.module.css";
import { RARITY_LABELS } from "@/lib/constants";
import type { Rarity } from "@/lib/types";

interface CardRarityBadgeProps {
  rarity: Rarity;
}

const rarityColors: Record<string, string> = {
  common: "var(--color-rarity-common)",
  rare: "var(--color-rarity-rare)",
  epic: "var(--color-rarity-epic)",
  legendary: "var(--color-rarity-legendary)",
};

export function CardRarityBadge({ rarity }: CardRarityBadgeProps) {
  return (
    <span
      className={styles.badge}
      style={{ backgroundColor: rarityColors[rarity] ?? "var(--color-rarity-common)" }}
      title={RARITY_LABELS[rarity] ?? rarity}
    />
  );
}
