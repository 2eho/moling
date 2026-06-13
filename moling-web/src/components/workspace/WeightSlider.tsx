"use client";

import { useState, useCallback } from "react";
import styles from "./WeightSlider.module.css";

interface WeightSliderProps {
  value: number;
  onChange: (value: number) => void;
  min?: number;
  max?: number;
}

export function WeightSlider({
  value,
  onChange,
  min = 0,
  max = 100,
}: WeightSliderProps) {
  const [showValue, setShowValue] = useState(false);

  const handleChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      onChange(Number(e.target.value));
    },
    [onChange],
  );

  return (
    <div className={styles.slider}>
      <span className={styles.label}>权重</span>
      <div className={styles.trackContainer}>
        <input
          type="range"
          min={min}
          max={max}
          value={value}
          onChange={handleChange}
          onMouseEnter={() => setShowValue(true)}
          onMouseLeave={() => setShowValue(false)}
          className={styles.input}
        />
        <div
          className={styles.fill}
          style={{ width: `${value}%` }}
        />
      </div>
      {(showValue || value !== 50) && (
        <span className={styles.value}>{value}</span>
      )}
    </div>
  );
}
