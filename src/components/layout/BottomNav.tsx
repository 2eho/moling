import React, { useState, useEffect, useRef, useCallback } from 'react';
import styles from './BottomNav.module.css';

export interface TouchGestureHandlers {
  onSwipeLeft?: () => void;
  onSwipeRight?: () => void;
  onSwipeUp?: () => void;
  onSwipeDown?: () => void;
}

interface BottomNavProps {
  activeTab?: 'write' | 'library' | 'more';
  onTabChange?: (tab: 'write' | 'library' | 'more') => void;
  gestureHandlers?: TouchGestureHandlers;
  isEditorFullscreen?: boolean;
}

const BottomNav: React.FC<BottomNavProps> = ({
  activeTab = 'write',
  onTabChange,
  gestureHandlers,
  isEditorFullscreen = false,
}) => {
  const [isMoreMenuOpen, setIsMoreMenuOpen] = useState(false);
  const [isVisible, setIsVisible] = useState(true);
  const navRef = useRef<HTMLDivElement>(null);
  const moreMenuRef = useRef<HTMLDivElement>(null);

  // 切换更多菜单
  const toggleMoreMenu = useCallback(() => {
    setIsMoreMenuOpen(prev => !prev);
  }, []);

  // 关闭更多菜单
  const closeMoreMenu = useCallback(() => {
    setIsMoreMenuOpen(false);
  }, []);

  // 处理导航项点击
  const handleTabClick = useCallback((tab: 'write' | 'library' | 'more') => {
    if (tab === 'more') {
      toggleMoreMenu();
    } else {
      closeMoreMenu();
      onTabChange?.(tab);
    }
  }, [toggleMoreMenu, closeMoreMenu, onTabChange]);

  // 点击外部区域关闭更多菜单
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent | TouchEvent) => {
      if (
        moreMenuRef.current &&
        !moreMenuRef.current.contains(event.target as Node) &&
        navRef.current &&
        !navRef.current.contains(event.target as Node)
      ) {
        closeMoreMenu();
      }
    };

    if (isMoreMenuOpen) {
      document.addEventListener('mousedown', handleClickOutside);
      document.addEventListener('touchstart', handleClickOutside);
    }

    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
      document.removeEventListener('touchstart', handleClickOutside);
    };
  }, [isMoreMenuOpen, closeMoreMenu]);

  // 触摸手势监听（预留接口）
  useEffect(() => {
    if (!gestureHandlers) return;

    let touchStartX = 0;
    let touchStartY = 0;
    const swipeThreshold = 50;

    const handleTouchStart = (e: TouchEvent) => {
      touchStartX = e.touches[0].clientX;
      touchStartY = e.touches[0].clientY;
    };

    const handleTouchEnd = (e: TouchEvent) => {
      const touchEndX = e.changedTouches[0].clientX;
      const touchEndY = e.changedTouches[0].clientY;
      
      const deltaX = touchEndX - touchStartX;
      const deltaY = touchEndY - touchStartY;

      const absDeltaX = Math.abs(deltaX);
      const absDeltaY = Math.abs(deltaY);

      // 判断是否为滑动手势
      if (Math.max(absDeltaX, absDeltaY) < swipeThreshold) return;

      if (absDeltaX > absDeltaY) {
        // 水平滑动
        if (deltaX > 0) {
          gestureHandlers.onSwipeRight?.();
        } else {
          gestureHandlers.onSwipeLeft?.();
        }
      } else {
        // 垂直滑动
        if (deltaY > 0) {
          gestureHandlers.onSwipeDown?.();
        } else {
          gestureHandlers.onSwipeUp?.();
        }
      }
    };

    document.addEventListener('touchstart', handleTouchStart, { passive: true });
    document.addEventListener('touchend', handleTouchEnd, { passive: true });

    return () => {
      document.removeEventListener('touchstart', handleTouchStart);
      document.removeEventListener('touchend', handleTouchEnd);
    };
  }, [gestureHandlers]);

  // 编辑器全屏时的自动隐藏逻辑
  useEffect(() => {
    if (!isEditorFullscreen) {
      setIsVisible(true);
      return;
    }

    let lastScrollY = window.scrollY;
    const handleScroll = () => {
      const currentScrollY = window.scrollY;
      if (currentScrollY > lastScrollY) {
        // 下滑隐藏
        setIsVisible(false);
      } else {
        // 上滑显示
        setIsVisible(true);
      }
      lastScrollY = currentScrollY;
    };

    window.addEventListener('scroll', handleScroll, { passive: true });
    return () => window.removeEventListener('scroll', handleScroll);
  }, [isEditorFullscreen]);

  return (
    <>
      {/* 更多菜单 */}
      {isMoreMenuOpen && (
        <div className={styles.moreMenuOverlay} onClick={closeMoreMenu}>
          <div className={styles.moreMenu} ref={moreMenuRef} onClick={e => e.stopPropagation()}>
            <button className={styles.menuItem}>
              <span className={styles.menuIcon}>📚</span>
              <span className={styles.menuLabel}>切换项目</span>
            </button>
            <button className={styles.menuItem}>
              <span className={styles.menuIcon}>🔔</span>
              <span className={styles.menuLabel}>通知</span>
            </button>
            <button className={styles.menuItem}>
              <span className={styles.menuIcon}>⚙️</span>
              <span className={styles.menuLabel}>设置</span>
            </button>
            <button className={styles.menuItem}>
              <span className={styles.menuIcon}>👤</span>
              <span className={styles.menuLabel}>个人资料</span>
            </button>
          </div>
        </div>
      )}

      {/* 底部导航 */}
      <nav
        ref={navRef}
        className={`${styles.bottomNav} ${isVisible ? styles.visible : styles.hidden}`}
        style={{
          paddingBottom: 'env(safe-area-inset-bottom)',
        }}
      >
        <button
          className={`${styles.navItem} ${activeTab === 'write' ? styles.active : ''}`}
          onClick={() => handleTabClick('write')}
          aria-label="写作"
        >
          <span className={styles.navIcon}>✒️</span>
          <span className={styles.navLabel}>写作</span>
        </button>

        <button
          className={`${styles.navItem} ${activeTab === 'library' ? styles.active : ''}`}
          onClick={() => handleTabClick('library')}
          aria-label="四库"
        >
          <span className={styles.navIcon}>📖</span>
          <span className={styles.navLabel}>四库</span>
        </button>

        <button
          className={`${styles.navItem} ${activeTab === 'more' || isMoreMenuOpen ? styles.active : ''}`}
          onClick={() => handleTabClick('more')}
          aria-label="更多"
          aria-expanded={isMoreMenuOpen}
        >
          <span className={styles.navIcon}>⋮</span>
          <span className={styles.navLabel}>更多</span>
        </button>
      </nav>
    </>
  );
};

export default BottomNav;
