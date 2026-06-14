'use client';

import { useState } from 'react';
import styles from './pricing.module.css';

const PLANS = [
  {
    id: 'free',
    name: '免费版',
    price: { monthly: 0, yearly: 0 },
    description: '适合初次体验墨灵的创作者',
    features: ['最多 3 个项目', '每月 50 章', '基础写作 + 卡牌池', '四库管理'],
    disabledFeatures: ['优先生成队列', '全量重新分析', '团队协作'],
    cta: '当前方案',
    popular: false,
  },
  {
    id: 'pro',
    name: 'Pro',
    price: { monthly: 29.9, yearly: 299 },
    description: '专业作者的首选',
    features: [
      '无限项目',
      '无限章节',
      '优先生成队列',
      '全量重新分析',
      '优先技术支持',
    ],
    disabledFeatures: ['团队协作'],
    cta: '立即订阅',
    popular: true,
  },
  {
    id: 'enterprise',
    name: '企业版',
    price: { monthly: 99.9, yearly: 999 },
    description: '适合工作室和创作团队',
    features: [
      '全部 Pro 功能',
      '多人协作',
      '权限管理',
      '共享资料库与卡牌池',
      '专属客户经理',
      '99.9% SLA',
    ],
    disabledFeatures: [],
    cta: '联系销售',
    popular: false,
  },
];

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

  const yearlyMonthlyEquivalent = (yearlyPrice: number, monthlyPrice: number) => {
    const perMonth = +(yearlyPrice / 12).toFixed(1);
    const saving = Math.round((1 - perMonth / monthlyPrice) * 100);
    return saving;
  };

  const handleSubscribe = (planId: string) => {
    if (planId === 'free') {
      window.location.href = '/auth/register';
      return;
    }
    if (planId === 'enterprise') {
      window.alert('感谢您的关注！我们的销售团队将在 24 小时内与您联系。');
      return;
    }
    window.alert('支付页面将打开（演示模式）');
  };

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

      {/* Billing Toggle */}
      <div className={styles.billingToggle}>
        <span
          className={`${styles.toggleLabel} ${billingCycle === 'monthly' ? styles.toggleLabelActive : ''}`}
          onClick={() => setBillingCycle('monthly')}
        >
          月付
        </span>
        <div
          className={`${styles.toggleTrack} ${billingCycle === 'yearly' ? styles.toggleTrackActive : ''}`}
          onClick={() => setBillingCycle(billingCycle === 'monthly' ? 'yearly' : 'monthly')}
        >
          <div className={styles.toggleKnob} />
        </div>
        <span
          className={`${styles.toggleLabel} ${billingCycle === 'yearly' ? styles.toggleLabelActive : ''}`}
          onClick={() => setBillingCycle('yearly')}
        >
          年付
          <span className={styles.saveBadge} style={{ marginLeft: 6 }}>
            省 2 个月
          </span>
        </span>
      </div>

      {/* Plan Cards */}
      <div className={styles.cards}>
        {PLANS.map((plan) => {
          const price = plan.price[billingCycle];
          const monthlyPrice = plan.price.monthly;
          const yearlyPrice = plan.price.yearly;

          return (
            <div key={plan.id} className={`${styles.card} ${plan.popular ? styles.cardPopular : ''}`}>
              {plan.popular && <div className={styles.popularBadge}>最受欢迎</div>}

              <div className={styles.planName}>{plan.name}</div>
              <div className={styles.planDesc}>{plan.description}</div>

              <div className={styles.planPrice}>
                {price > 0 && <span className={styles.priceCurrency}>¥</span>}
                <span className={styles.priceAmount}>{price}</span>
                <span className={styles.pricePeriod}>
                  {price > 0 ? (billingCycle === 'monthly' ? '/月' : '/年') : '/月'}
                </span>
                {billingCycle === 'yearly' && price > 0 && monthlyPrice > 0 && (
                  <span className={styles.priceOriginal}>
                    ¥{(monthlyPrice * 12).toFixed(1)}
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
                {plan.disabledFeatures.map((f, i) => (
                  <li key={i} className={styles.featureDisabled}>
                    <svg className={styles.featureDash} width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <line x1="5" y1="12" x2="19" y2="12" />
                    </svg>
                    {f}
                  </li>
                ))}
              </ul>

              <button
                className={`${plan.popular ? styles.planCtaPrimary : styles.planCta}`}
                onClick={() => handleSubscribe(plan.id)}
              >
                {plan.cta}
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
