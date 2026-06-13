"use client";

import { useState } from "react";
import styles from "./Input.module.css";

interface InputProps extends Omit<React.InputHTMLAttributes<HTMLInputElement>, "size"> {
  label?: string;
  error?: string;
  icon?: string;
}

export function Input({
  label,
  error,
  icon,
  className,
  ...rest
}: InputProps) {
  const [focused, setFocused] = useState(false);

  const classes = [
    styles.wrapper,
    error ? styles.hasError : "",
    focused ? styles.isFocused : "",
    className ?? "",
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <div className={classes}>
      {label && <label className={styles.label}>{label}</label>}
      <div className={styles.inputContainer}>
        {icon && <span className={styles.icon}>{icon}</span>}
        <input
          className={styles.input}
          onFocus={() => setFocused(true)}
          onBlur={() => setFocused(false)}
          {...rest}
        />
      </div>
      {error && <span className={styles.error}>{error}</span>}
    </div>
  );
}
