"use client";

import { useEffect, useRef, type RefObject } from "react";

export interface TouchGestureOptions {
  /** 左滑回调（打开参考面板） */
  onSwipeLeft?: () => void;
  /** 右滑回调（打开 AI 面板） */
  onSwipeRight?: () => void;
  /** 上滑回调（显示导航） */
  onSwipeUp?: () => void;
  /** 下滑回调（隐藏导航） */
  onSwipeDown?: () => void;
  /** 点击回调（非滑动） */
  onTap?: (event: TouchEvent) => void;
  /** 滑动阈值（px），默认 50 */
  threshold?: number;
  /** 是否启用，默认 true */
  enabled?: boolean;
}

export function useTouchGesture<T extends HTMLElement = HTMLElement>(
  options: TouchGestureOptions,
  targetRef?: RefObject<T>
) {
  const {
    onSwipeLeft,
    onSwipeRight,
    onSwipeUp,
    onSwipeDown,
    onTap,
    threshold = 50,
    enabled = true,
  } = options;

  const touchStartRef = useRef<{ x: number; y: number; time: number } | null>(null);
  const elementRef = useRef<T | null>(null);

  useEffect(() => {
    if (!enabled) return;

    const element = targetRef?.current || elementRef.current;
    if (!element) return;

    const handleTouchStart = (event: TouchEvent) => {
      const touch = event.touches[0];
      touchStartRef.current = {
        x: touch.clientX,
        y: touch.clientY,
        time: Date.now(),
      };
    };

    const handleTouchEnd = (event: TouchEvent) => {
      if (!touchStartRef.current) return;

      const touch = event.changedTouches[0];
      const deltaX = touch.clientX - touchStartRef.current.x;
      const deltaY = touch.clientY - touchStartRef.current.y;
      const deltaTime = Date.now() - touchStartRef.current.time;

      // 重置起始点
      touchStartRef.current = null;

      // 判断是否为点击（移动距离小，时间短）
      const isTap =
        Math.abs(deltaX) < 10 &&
        Math.abs(deltaY) < 10 &&
        deltaTime < 300;

      if (isTap) {
        onTap?.(event);
        return;
      }

      // 判断滑动方向（只处理主要方向）
      const isHorizontal = Math.abs(deltaX) > Math.abs(deltaY);
      const isVertical = Math.abs(deltaY) > Math.abs(deltaX);

      if (isHorizontal && Math.abs(deltaX) >= threshold) {
        if (deltaX > 0) {
          onSwipeRight?.();
        } else {
          onSwipeLeft?.();
        }
      } else if (isVertical && Math.abs(deltaY) >= threshold) {
        if (deltaY > 0) {
          onSwipeDown?.();
        } else {
          onSwipeUp?.();
        }
      }
    };

    element.addEventListener("touchstart", handleTouchStart as any, { passive: true });
    element.addEventListener("touchend", handleTouchEnd as any, { passive: true });

    return () => {
      element.removeEventListener("touchstart", handleTouchStart as any);
      element.removeEventListener("touchend", handleTouchEnd as any);
    };
  }, [enabled, threshold, onSwipeLeft, onSwipeRight, onSwipeUp, onSwipeDown, onTap, targetRef]);

  return elementRef;
}
