'use client';

import { useState, useCallback, useEffect } from 'react';
import { useAuth } from '@/hooks/useAuth';
import { subscriptionApi } from '@/lib/api';
import { showToast } from '@/components/ui/Toast';
import styles from './page.module.css';

/* ============================================
   定价数据
   ============================================ */

interface PlanFeature {
  label: string;
  free: boolean | string;
  pro: boolean | string;
  team: boolean | string;
}

interface PriceData {
  monthly: string;
  yearly: string;
  periodMonthly: string;
  periodYearly: string;
  originalYearly: string;
}

interface Plan {
  name: string;
  desc: string;
  price: PriceData;
  features: { label: string; enabled: boolean }[];
  ctaLabel: string;
  ctaHref: string;
  ctaVariant: 'default' | 'primary' | 'current';
  popular: boolean;
}

const plans: Plan[] = [
  {
    name: '免费版',
    desc: '适合初次体验墨灵的创作者',
    price: {
      monthly: '¥0',
      yearly: '¥0',
      periodMonthly: '/ 月',
      periodYearly: '/ 月',
      originalYearly: '',
    },
    features: [
      { label: '最多 3 个项目', enabled: true },
      { label: '每月 50 章', enabled: true },
      { label: '基础写作 + 卡牌池', enabled: true },
      { label: '四库管理', enabled: true },
      { label: '优先生成队列', enabled: false },
      { label: '全量重新分析', enabled: false },
      { label: '团队协作', enabled: false },
    ],
    ctaLabel: '当前方案',
    ctaHref: '/auth',
    ctaVariant: 'current',
    popular: false,
  },
  {
    name: 'Pro',
    desc: '专业作者的首选',
    price: {
      monthly: '¥29.9',
      yearly: '¥299',
      periodMonthly: '/ 月',
      periodYearly: '/ 年',
      originalYearly: '¥358.8',
    },
    features: [
      { label: '无限项目', enabled: true },
      { label: '无限章节', enabled: true },
      { label: '优先生成队列', enabled: true },
      { label: '全量重新分析', enabled: true },
      { label: '专属技术支持', enabled: true },
      { label: '团队协作', enabled: false },
    ],
    ctaLabel: '立即订阅',
    ctaHref: '/api/v1/subscriptions/create-checkout?plan=pro',
    ctaVariant: 'primary',
    popular: true,
  },
  {
    name: '团队版',
    desc: '工作室和创作团队',
    price: {
      monthly: '¥99.9',
      yearly: '¥999',
      periodMonthly: '/ 月',
      periodYearly: '/ 年',
      originalYearly: '¥1,198.8',
    },
    features: [
      { label: 'Pro 全部功能', enabled: true },
      { label: '多人实时协作', enabled: true },
      { label: '权限管理', enabled: true },
      { label: '共享四库和卡牌池', enabled: true },
      { label: '专属客户经理', enabled: true },
      { label: '99.9% SLA', enabled: true },
    ],
    ctaLabel: '联系销售',
    ctaHref: '/auth',
    ctaVariant: 'default',
    popular: false,
  },
];

/* ── 特性对比表 ── */

const compareFeatures: PlanFeature[] = [
  { label: '项目数', free: '3 个', pro: '无限', team: '无限' },
  { label: '月章节上限', free: '50 章', pro: '无限', team: '无限' },
  { label: 'AI 写作', free: true, pro: true, team: true },
  { label: '卡牌池 + 抽卡', free: true, pro: true, team: true },
  { label: '四库管理', free: true, pro: true, team: true },
  { label: '优先生成', free: false, pro: true, team: true },
  { label: '全量重新分析', free: false, pro: true, team: true },
  { label: '多人协作', free: false, pro: false, team: true },
  { label: 'API 访问', free: false, pro: false, team: true },
  { label: '专属支持', free: false, pro: true, team: true },
];

function renderFeatureValue(value: boolean | string): { text: string; isYes: boolean } {
  if (value === true) return { text: '✓', isYes: true };
  if (value === false) return { text: '—', isYes: false };
  return { text: String(value), isYes: false };
}

/* ============================================
   页面组件
   ============================================ */

export default function PricingPage() {
  const [yearly, setYearly] = useState(false);
  const [toastMsg, setToastMsg] = useState('');
  const [toastVisible, setToastVisible] = useState(false);
  const { isAuthenticated } = useAuth();

  const toggleBilling = useCallback(() => {
    setYearly((prev) => !prev);
  }, []);

  const showToast = useCallback((msg: string) => {
    setToastMsg(msg);
    setToastVisible(true);
    setTimeout(() => {
      setToastVisible(false);
    }, 2500);
  }, []);

  const handleSubscribe = useCallback(
    async (e: React.MouseEvent<HTMLAnchorElement>, planName: string) => {
      e.preventDefault();
      
      // Check auth status (from closure)
      if (!isAuthenticated) {
        // Redirect to login
        window.location.href = '/auth?redirect=' + encodeURIComponent(window.location.pathname);
        return;
      }

      try {
        showToast('info', '跳转支付中...');
        const response = await subscriptionApi.createCheckout(
          planName.toLowerCase(),
          window.location.origin + '/pricing?success=true',
          window.location.origin + '/pricing?cancel=true'
        );
        // Redirect to checkout URL
        window.location.href = response.data.checkout_url;
      } catch (error) {
        showToast('error', '创建订阅失败，请重试');
        console.error('Subscription checkout failed:', error);
      }
    },
    [showToast, isAuthenticated],
  );

  return (
    <div className={styles.container}>
      {/* 导航 */}
      <nav className={styles.nav}>
        <div className={styles.navBrand}>
          <span>墨</span>灵
        </div>
        <div className={styles.navLinks}>
          <a href="/">首页</a>
          <a href="/pricing" className={styles.navLinkActive}>
            定价
          </a>
          <a href="/auth">登录</a>
          <a href="/auth" className={styles.navBtn}>
            开始创作
          </a>
        </div>
      </nav>

      {/* 头部 */}
      <section className={styles.hero}>
        <h1>选择适合你的创作方案</h1>
        <p>
          免费版让你体验核心功能，Pro 版释放全部创作力，团队版支持多人协作。
        </p>
      </section>

      {/* 计费切换 */}
      <div className={styles.billingToggle}>
        <span>月付</span>
        <div
          className={`${styles.toggleTrack} ${yearly ? styles.toggleTrackActive : ''}`}
          onClick={toggleBilling}
          role="button"
          tabIndex={0}
          onKeyDown={(e) => {
            if (e.key === 'Enter' || e.key === ' ') {
              e.preventDefault();
              toggleBilling();
            }
          }}
          aria-label="切换年付/月付"
        >
          <div className={styles.toggleKnob} />
        </div>
        <span>年付</span>
        <span className={styles.saveBadge}>省 2 个月</span>
      </div>

      {/* 套餐卡片 */}
      <div className={styles.plans}>
        {plans.map((plan) => {
          const amount = yearly ? plan.price.yearly : plan.price.monthly;
          const period = yearly ? plan.price.periodYearly : plan.price.periodMonthly;
          const showOriginal = yearly && !!plan.price.originalYearly;

          const ctaClass = [
            styles.planCta,
            plan.ctaVariant === 'primary' ? styles.planCtaPrimary : '',
            plan.ctaVariant === 'current' ? styles.planCtaCurrent : '',
          ]
            .filter(Boolean)
            .join(' ');

          return (
            <div
              key={plan.name}
              className={`${styles.planCard} ${plan.popular ? styles.planCardPopular : ''}`}
            >
              <div className={styles.planName}>{plan.name}</div>
              <div className={styles.planDesc}>{plan.desc}</div>
              <div className={styles.planPrice}>
                <span className={styles.amount}>{amount}</span>{' '}
                <span className={styles.period}>{period}</span>
                {showOriginal && (
                  <span className={styles.original}>{plan.price.originalYearly}</span>
                )}
              </div>
              <ul className={styles.planFeatures}>
                {plan.features.map((feat) => (
                  <li
                    key={feat.label}
                    className={`${styles.featureItem} ${!feat.enabled ? styles.featureDisabled : ''}`}
                  >
                    {feat.label}
                  </li>
                ))}
              </ul>
              <a
                className={ctaClass}
                href={plan.ctaHref}
                onClick={(e) => handleSubscribe(e, plan.name)}
              >
                {plan.ctaLabel}
              </a>
            </div>
          );
        })}
      </div>

      {/* 完整功能对比 */}
      <section className={styles.featuresCompare}>
        <h2>完整功能对比</h2>
        <table className={styles.fTable}>
          <thead>
            <tr>
              <th>功能</th>
              <th>免费版</th>
              <th>Pro</th>
              <th>团队版</th>
            </tr>
          </thead>
          <tbody>
            {compareFeatures.map((feat) => {
              const free = renderFeatureValue(feat.free);
              const pro = renderFeatureValue(feat.pro);
              const team = renderFeatureValue(feat.team);
              return (
                <tr key={feat.label}>
                  <td>{feat.label}</td>
                  <td className={free.isYes ? styles.fYes : styles.fNo}>
                    {free.text}
                  </td>
                  <td className={pro.isYes ? styles.fYes : styles.fNo}>
                    {pro.text}
                  </td>
                  <td className={team.isYes ? styles.fYes : styles.fNo}>
                    {team.text}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </section>

      {/* 页脚 */}
      <footer className={styles.footer}>
        <div>
          <a href="/">首页</a>
          <a href="/pricing">定价</a>
          <a href="/help">帮助</a>
          <a href="#">服务协议</a>
          <a href="#">隐私政策</a>
        </div>
        <div className={styles.footerCopy}>
          © 2026 墨灵 · AI 驱动创作平台
        </div>
      </footer>

      {/* Toast */}
      <div
        className={`${styles.toast} ${toastVisible ? styles.toastVisible : ''}`}
        id="toast"
      >
        {toastMsg}
      </div>
    </div>
  );
}
