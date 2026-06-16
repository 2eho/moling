'use client';

export const dynamic = 'force-dynamic';


import { useState, useEffect, useCallback } from 'react';
import styles from './pricing.module.css';
import { subscriptionApi } from '@/lib/api';
import type { SubscriptionPlanDetails, Subscription } from '@/lib/types';

const FAQ_ITEMS = [
  {
    q: '可以随时取消订阅吗？',
    a: '是的，你可以随时取消。取消后，你将继续享受当前订阅周期内的服务，到期后自动降级为免费版。',
  },
  {
    q: '生成次数用完了怎么办？',
    a: '免费版每月自动重置。如果你需要更多，可以升级到 Pro 或企业版获得无限生成次数。',
  },
  {
    q: '支持哪些支付方式？',
    a: '我们支持支付宝、微信支付、银联和信用卡。所有支付均通过加密渠道处理，安全可靠。',
  },
  {
    q: '有学生优惠吗？',
    a: '有的！在校学生可享受五折优惠。请使用教育邮箱注册或联系客服进行验证。',
  },
];

export default function PricingPage() {
  const [billingCycle, setBillingCycle] = useState<'monthly' | 'yearly'>('monthly');
  const [plans, setPlans] = useState<SubscriptionPlanDetails[]>([]);
  const [currentSubscription, setCurrentSubscription] = useState<Subscription | null>(null);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const [plansResult, subResult] = await Promise.all([
        subscriptionApi.getPlans(),
        subscriptionApi.getCurrent().catch(() => null),
      ]);
      setPlans(plansResult.data || []);
      if (subResult) {
        setCurrentSubscription(subResult.data || null);
      }
    } catch (error) {
      console.error('Failed to load pricing data:', error);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleSubscribe = async (planId: string) => {
    if (planId === 'free') {
      window.location.href = '/auth/register';
      return;
    }

    if (currentSubscription?.plan === planId && currentSubscription?.status === 'active') {
      alert('您当前已订阅此方案');
      return;
    }

    setActionLoading(planId);
    try {
      const successUrl = `${window.location.origin}/pricing?success=true`;
      const cancelUrl = `${window.location.origin}/pricing?canceled=true`;
      const result = await subscriptionApi.createCheckout(planId, successUrl, cancelUrl);
      if (result.data?.checkout_url) {
        window.location.href = result.data.checkout_url;
      } else {
        alert('创建支付会话失败，请稍后重试');
      }
    } catch (error) {
      console.error('Failed to create checkout:', error);
      alert('创建支付会话失败，请稍后重试');
    } finally {
      setActionLoading(null);
    }
  };

  if (loading) {
    return (
      <div className={styles.container}>
        <div className={styles.loading}>加载中...</div>
      </div>
    );
  }

  return (
    <div className={styles.container}>
      {/* Navigation */}
      <nav className={styles.nav}>
        <div className={styles.navBrand}>
          <span className={styles.navBrandAccent}>墨</span>灵
        </div>
        <div className={styles.navLinks}>
          <a href="/" className={styles.navLink}>首页</a>
          <a href="/pricing" className={`${styles.navLink} ${styles.navLinkActive}`}>定价</a>
          <a href="/auth" className={styles.navLink}>登录</a>
          <a href="/auth" className={styles.navBtn}>开始创作</a>
        </div>
      </nav>

      {/* Hero */}
      <section className={styles.hero}>
        <h1 className={styles.heroTitle}>选择适合你的创作方案</h1>
        <p className={styles.heroDesc}>免费版让你体验核心功能，Pro 版释放全部创作力，企业版支持团队协作。</p>
      </section>

      {/* Plan Cards */}
      <div className={styles.cards}>
        {plans.map((plan) => {
          const isCurrentPlan = currentSubscription?.plan === plan.id && currentSubscription?.status === 'active';
          const isPopular = plan.id === 'pro';

          return (
            <div key={plan.id} className={`${styles.card} ${isPopular ? styles.cardPopular : ''}`}>
              {isPopular && <div className={styles.popularBadge}>最受欢迎</div>}

              <div className={styles.planName}>{plan.name}</div>
              <div className={styles.planDesc}>{plan.description}</div>

              <div className={styles.planPrice}>
                {plan.price_monthly > 0 && <span className={styles.priceCurrency}>¥</span>}
                <span className={styles.priceAmount}>{billingCycle === 'monthly' ? plan.price_monthly : plan.price_yearly}</span>
                <span className={styles.pricePeriod}>
                  {plan.price_monthly > 0 ? (billingCycle === 'monthly' ? '/月' : '/年') : '/月'}
                </span>
                {billingCycle === 'yearly' && plan.price_monthly > 0 && (
                  <span className={styles.priceOriginal}>
                    ¥{(plan.price_monthly * 12).toFixed(1)}
                  </span>
                )}
              </div>

              <ul className={styles.features}>
                {plan.features.map((f, i) => (
                  <li key={i} className={styles.featureItem}>
                    <svg className={styles.featureCheck} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
                      <polyline points="20 6 9 17 4 12" />
                    </svg>
                    {f}
                  </li>
                ))}
              </ul>

              <button
                className={`${isPopular ? styles.planCtaPrimary : styles.planCta}`}
                onClick={() => handleSubscribe(plan.id)}
                disabled={actionLoading === plan.id || isCurrentPlan}
              >
                {actionLoading === plan.id ? '处理中...' : isCurrentPlan ? '当前方案' : '立即订阅'}
              </button>
            </div>
          );
        })}
      </div>

      {/* FAQ */}
      <section className={styles.faq}>
        <h2 className={styles.faqTitle}>常见问题</h2>
        <div className={styles.faqList}>
          {FAQ_ITEMS.map((item, i) => (
            <div key={i} className={styles.faqItem}>
              <h4 className={styles.faqQuestion}>{item.q}</h4>
              <p className={styles.faqAnswer}>{item.a}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Footer */}
      <footer className={styles.footer}>
        <div className={styles.footerLinks}>
          <a href="/" className={styles.footerLink}>首页</a>
          <a href="/pricing" className={styles.footerLink}>定价</a>
          <a href="/help" className={styles.footerLink}>帮助</a>
          <a href="#" className={styles.footerLink}>服务条款</a>
          <a href="#" className={styles.footerLink}>隐私政策</a>
        </div>
        <div>2026 墨灵 · AI 驱动的创作平台</div>
      </footer>
    </div>
  );
}
