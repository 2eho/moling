"use client";

import styles from "./CreationModeCard.module.css";

interface CreationModeCardProps {
  id: string;
  title: string;
  description: string;
  icon: string;
  selected: boolean;
  onClick: () => void;
}

export function CreationModeCard({
  id,
  title,
  description,
  icon,
  selected,
  onClick,
}: CreationModeCardProps) {
  return (
    <div
      className={`${styles.card} ${selected ? styles.selected : ""}`}
      onClick={onClick}
    >
      <span className={styles.icon}>{icon}</span>
      <div className={styles.info}>
        <h3 className={styles.title}>{title}</h3>
        <p className={styles.description}>{description}</p>
      </div>
      {selected && <span className={styles.checkmark}>✓</span>}
    </div>
  );
}
