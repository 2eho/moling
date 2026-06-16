import { useEffect, useRef, useCallback } from 'react';

/**
 * 触摸手势方向枚举
 */
export type SwipeDirection = 'left' | 'right' | 'up' | 'down';

/**
 * 手势事件回调接口
 */
export interface TouchGestureHandlers {
  /** 左滑 → 打开参考面板 */
  onSwipeLeft?: () => void;
  /** 右滑 → 打开 AI 面板 */
  onSwipeRight?: () => void;
  /** 上滑 → 显示导航 */
  onSwipeUp?: () => void;
  /** 下滑 → 隐藏导航 */
  onSwipeDown?: () => void;
  /** 点击（非滑动） */
  onTap?: (event: TouchEvent) => void;
}

/**
 * 手势配置选项
 */
export interface UseTouchGestureOptions {
  /** 滑动阈值（像素），默认 50 */
  swipeThreshold?: number;
  /** 是否启用水平滑动检测，默认 true */
  enableHorizontal?: boolean;
  /** 是否启用垂直滑动检测，默认 true */
  enableVertical?: boolean;
  /** 目标元素，默认 document */
  target?: React.RefObject<HTMLElement> | null;
}

/**
 * 触摸手势 Hook
 * 
 * 用于检测移动端的滑动手势，预留给 BottomNav 和其他组件使用。
 * 
 * @param handlers 手势事件回调
 * @param options 配置选项
 * 
 * @example
 * ```tsx
 * useTouchGesture(
 *   {
 *     onSwipeLeft: () => openReferencePanel(),
 *     onSwipeRight: () => openAIPanel(),
 *     onSwipeUp: () => showNavigation(),
 *     onSwipeDown: () => hideNavigation(),
 *   },
 *   { swipeThreshold: 60 }
 * );
 * ```
 */
export function useTouchGesture(
  handlers: TouchGestureHandlers,
  options: UseTouchGestureOptions = {}
) {
  const {
    swipeThreshold = 50,
    enableHorizontal = true,
    enableVertical = true,
    target = null,
  } = options;

  // 使用 ref 来存储触摸起始位置
  const touchStartRef = useRef<{ x: number; y: number } | null>(null);
  
  // 使用 ref 来存储 handlers，避免频繁触发 effect
  const handlersRef = useRef(handlers);
  handlersRef.current = handlers;

  // 触摸开始
  const handleTouchStart = useCallback((event: Event) => {
    const touchEvent = event as TouchEvent;
    const touch = touchEvent.touches[0];
    touchStartRef.current = {
      x: touch.clientX,
      y: touch.clientY,
    };
  }, []);

  // 触摸结束
  const handleTouchEnd = useCallback((event: Event) => {
    if (!touchStartRef.current) return;

    const touchEvent = event as TouchEvent;
    const touch = touchEvent.changedTouches[0];
    const deltaX = touch.clientX - touchStartRef.current.x;
    const deltaY = touch.clientY - touchStartRef.current.y;

    const absDeltaX = Math.abs(deltaX);
    const absDeltaY = Math.abs(deltaY);

    // 判断是否为点击（移动距离很小）
    const isTap = Math.max(absDeltaX, absDeltaY) < 10;
    if (isTap) {
      handlersRef.current.onTap?.(touchEvent);
      touchStartRef.current = null;
      return;
    }

    // 判断是否为有效滑动
    const isHorizontalSwipe = enableHorizontal && absDeltaX >= swipeThreshold;
    const isVerticalSwipe = enableVertical && absDeltaY >= swipeThreshold;

    if (!isHorizontalSwipe && !isVerticalSwipe) {
      touchStartRef.current = null;
      return;
    }

    // 确定滑动方向
    if (isHorizontalSwipe && absDeltaX > absDeltaY) {
      // 水平滑动
      if (deltaX > 0) {
        handlersRef.current.onSwipeRight?.();
      } else {
        handlersRef.current.onSwipeLeft?.();
      }
    } else if (isVerticalSwipe) {
      // 垂直滑动
      if (deltaY > 0) {
        handlersRef.current.onSwipeDown?.();
      } else {
        handlersRef.current.onSwipeUp?.();
      }
    }

    touchStartRef.current = null;
  }, [swipeThreshold, enableHorizontal, enableVertical]);

  // 添加/移除事件监听
  useEffect(() => {
    const element = target?.current || document;

    element.addEventListener('touchstart', handleTouchStart, { passive: true });
    element.addEventListener('touchend', handleTouchEnd, { passive: true });

    return () => {
      element.removeEventListener('touchstart', handleTouchStart);
      element.removeEventListener('touchend', handleTouchEnd);
    };
  }, [target, handleTouchStart, handleTouchEnd]);

  // 返回手动触发的方法（可选）
  return {
    /** 重置手势状态 */
    reset: () => {
      touchStartRef.current = null;
    },
  };
}

export default useTouchGesture;
