import React from 'react';
import { useNavigate } from 'react-router-dom';
import styles from './NotFound.module.css';

/**
 * 专业404页面组件
 * 深色主题 + indigo/amber 品牌色
 * 响应式设计（移动端 + Web端）
 */
const NotFound: React.FC = () => {
  const navigate = useNavigate();

  const handleGoHome = () => {
    navigate('/');
  };

  const handleGoBack = () => {
    if (window.history.length > 1) {
      navigate(-1);
    } else {
      navigate('/');
    }
  };

  return (
    <div className={styles.notFoundContainer}>
      {/* 装饰元素 */}
      <div className={`${styles.decoration} ${styles.decoration1}`} />
      <div className={`${styles.decoration} ${styles.decoration2}`} />

      <div className={styles.contentWrapper}>
        {/* 图标 */}
        <div className={styles.iconWrapper}>
          <span className={styles.icon}>🔍</span>
        </div>

        {/* 错误代码 */}
        <h1 className={styles.errorCode}>404</h1>

        {/* 标题 */}
        <h2 className={styles.title}>页面未找到</h2>

        {/* 描述 */}
        <p className={styles.description}>
          抱歉，您访问的页面不存在或已被移除。
          请检查网址是否正确，或返回首页继续创作。
        </p>

        {/* 按钮组 */}
        <div className={styles.buttonGroup}>
          <button
            className={styles.homeButton}
            onClick={handleGoHome}
            type="button"
          >
            <svg
              width="20"
              height="20"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" />
              <polyline points="9 22 9 12 15 12 15 22" />
            </svg>
            返回首页
          </button>

          <button
            className={styles.backButton}
            onClick={handleGoBack}
            type="button"
          >
            <svg
              width="20"
              height="20"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <line x1="19" y1="12" x2="5" y2="12" />
              <polyline points="12 19 5 12 12 5" />
            </svg>
            返回上一页
          </button>
        </div>
      </div>
    </div>
  );
};

export default NotFound;
