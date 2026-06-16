import React from 'react';
import styles from './LoadingSkeleton.module.css';

export type SkeletonShape = 'text' | 'title' | 'circle' | 'rectangle' | 'avatar' | 'button' | 'card' | 'listItem';
export type SkeletonWidth = '25' | '50' | '75' | '100';
export type SkeletonHeight = 'sm' | 'md' | 'lg';

interface LoadingSkeletonProps {
  /** 形状 */
  shape?: SkeletonShape;
  /** 自定义宽度 */
  width?: string;
  /** 自定义高度 */
  height?: string;
  /** 预设宽度 */
  presetWidth?: SkeletonWidth;
  /** 预设高度 */
  presetHeight?: SkeletonHeight;
  /** 自定义类名 */
  className?: string;
  /** 是否显示动画 */
  animate?: boolean;
}

interface SkeletonGroupProps {
  /** 骨架屏数量 */
  count: number;
  /** 骨架形状 */
  shape?: SkeletonShape;
  /** 自定义类名 */
  className?: string;
}

/**
 * 骨架屏组件
 * 支持多种预设形状 + 动画效果
 */
const LoadingSkeleton: React.FC<LoadingSkeletonProps> = ({
  shape = 'text',
  width,
  height,
  presetWidth,
  presetHeight,
  className = '',
  animate = true,
}) => {
  const skeletonClass = [
    styles.skeletonItem,
    styles[shape],
    presetWidth && styles[`width${presetWidth}`],
    presetHeight && styles[`height${presetHeight}`],
    !animate && styles.noAnimation,
    className,
  ]
    .filter(Boolean)
    .join(' ');

  const style: React.CSSProperties = {};
  if (width) style.width = width;
  if (height) style.height = height;

  return <div className={skeletonClass} style={style} />;
};

/**
 * 骨架屏组组件（方便批量生成）
 */
const SkeletonGroup: React.FC<SkeletonGroupProps> = ({
  count,
  shape = 'text',
  className = '',
}) => {
  return (
    <div className={styles.skeletonContainer}>
      {Array.from({ length: count }, (_, index) => (
        <LoadingSkeleton key={index} shape={shape} className={className} />
      ))}
    </div>
  );
};

export default LoadingSkeleton;
export { SkeletonGroup };
