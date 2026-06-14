'use client';

import { useState } from 'react';
import styles from './Pricing.module.css';

export default function PricingPage() {
  const [billingCycle, setBillingCycle] = useState<'monthly' | 'yearly'>('monthly');
  const [showPaymentModal, setShowPaymentModal] = useState(false);
  const [selectedPlan, setSelectedPlan] = useState<string | null>(null);

  const plans = [
    {
      id: 'free',
      name: '免费版',
      price: { monthly: 0, yearly: 0 },
      description: '适合新手创作者，体验基础功能',
      features: [
        '每月 5 次生成',
        '基础灵感卡牌',
        '四库管理（最多 20 条）',
        '社区支持',
      ],
      notIncluded: [
        '高级灵感卡牌',
        '优先生成速度',
        '导入分析',
        'API 访问',
      ],
      cta: '免费开始',
      popular: false,
    },
    {
      id: 'pro',
      name: '专业版',
      price: { monthly: 49, yearly: 390 },
      description: '适合活跃创作者，解锁全部功能',
      features: [
        '无限次生成',
        '全部灵感卡牌',
        '四库管理（无限）',
        '优先生成速度',
        '导入分析',
        '邮件支持',
      ],
      notIncluded: [
        'API 访问',
        '团队协作',
      ],
      cta: '立即订阅',
      popular: true,
    },
    {
      id: 'enterprise',
      name: '企业版',
      price: { monthly: 199, yearly: 1590 },
      description: '适合团队使用，高级功能全开',
      features: [
        '专业版全部功能',
        'API 访问',
        '团队协作（最多 10 人）',
        '自定义 AI 模型',
        '优先技术支持',
        '专属客户经理',
      ],
      notIncluded: [],
      cta: '联系销售',
      popular: false,
    },
  ];

  const handleSubscribe = (planId: string) => {
    if (planId === 'free') {
      window.location.href = '/auth/register';
      return;
    }

    if (planId === 'enterprise') {
      alert('感谢您的兴趣！我们的销售团队将在 24 小时内联系您。');
      return;
    }

    setSelectedPlan(planId);
    setShowPaymentModal(true);
  };

  const handlePayment = async () => {
    // Mock 支付处理
    await new Promise(resolve => setTimeout(resolve, 2000));
    alert('支付成功！感谢订阅。');
    setShowPaymentModal(false);
    setSelectedPlan(null);
  };

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <h1 className={styles.title}>选择适合您的方案</h1>
        <p className={styles.subtitle}>
          从免费开始，随着创作需求升级。所有方案均含核心 AI 功能。
        </p>
      </div>

      {/* Billing Toggle */}
      <div className={styles.billingToggle}>
        <span className={`${styles.toggleLabel} ${billingCycle === 'monthly' ? styles.toggleLabelActive : ''}`}>
          月付
        </span>
        <button
          className={styles.toggleBtn}
          onClick={() => setBillingCycle(billingCycle === 'monthly' ? 'yearly' : 'monthly')}
        >
          <div
            className={`${styles.toggleCircle} ${billingCycle === 'yearly' ? styles.toggleCircleYearly : ''}`}
          />
        </button>
        <span className={`${styles.toggleLabel} ${billingCycle === 'yearly' ? styles.toggleLabelActive : ''}`}>
          年付
          <span className={styles.saveBadge}>省 34%</span>
        </span>
      </div>

      {/* Pricing Cards */}
      <div className={styles.cards}>
        {plans.map(plan => (
          <div
            key={plan.id}
            className={`${styles.card} ${plan.popular ? styles.cardPopular : ''}`}
          >
            {plan.popular && (
              <div className={styles.popularBadge}>最受欢迎</div>
            )}

            <h3 className={styles.planName}>{plan.name}</h3>
            <div className={styles.planPrice}>
              <span className={styles.priceCurrency}>¥</span>
              <span className={styles.priceAmount}>
                {plan.price[billingCycle]}
              </span>
              {plan.price[billingCycle] > 0 && (
                <span className={styles.pricePeriod}>
                  /{billingCycle === 'monthly' ? '月' : '年'}
                </span>
              )}
            </div>
            <p className={styles.planDesc}>{plan.description}</p>

            <ul className={styles.features}>
              {plan.features.map((feature, index) => (
                <li key={index} className={styles.featureIncluded}>
                  <span className={styles.featureIcon}>✓</span>
                  {feature}
                </li>
              ))}
              {plan.notIncluded.map((feature, index) => (
                <li key={index} className={styles.featureNotIncluded}>
                  <span className={styles.featureIcon}>✗</span>
                  {feature}
                </li>
              ))}
            </ul>

            <button
              className={`${styles.planCta} ${plan.popular ? styles.planCtaPopular : ''}`}
              onClick={() => handleSubscribe(plan.id)}
            >
              {plan.cta}
            </button>
          </div>
        ))}
      </div>

      {/* FAQ */}
      <div className={styles.faq}>
        <h2 className={styles.faqTitle}>常见问题</h2>

        <div className={styles.faqList}>
          <div className={styles.faqItem}>
            <h4 className={styles.faqQuestion}>可以随时取消订阅吗？</h4>
            <p className={styles.faqAnswer}>
              是的，您可以随时取消订阅。取消后，您将继续享受当前订阅周期的服务，到期后自动降级到免费版。
            </p>
          </div>

          <div className={styles.faqItem}>
            <h4 className={styles.faqQuestion}>生成次数用完了怎么办？</h4>
            <p className={styles.faqAnswer}>
              免费版每月重置生成次数。如需更多次数，可以升级到专业版或企业版，享受无限次生成。
            </p>
          </div>

          <div className={styles.faqItem}>
            <h4 className={styles.faqQuestion}>支持哪些支付方式？</h4>
            <p className={styles.faqAnswer}>
              我们支持支付宝、微信支付、银联和信用卡支付。所有支付均通过加密通道处理，确保安全。
            </p>
          </div>

          <div className={styles.faqItem}>
            <h4 className={styles.faqQuestion}>有学生优惠吗？</h4>
            <p className={styles.faqAnswer}>
              有的！在校学生可享受 5 折优惠。请使用教育邮箱注册，或联系客服验证学生身份。
            </p>
          </div>
        </div>
      </div>

      {/* Payment Modal (Mock) */}
      {showPaymentModal && (
        <div className={styles.modalOverlay} onClick={(e) => e.target === e.currentTarget && setShowPaymentModal(false)}>
          <div className={styles.modal}>
            <div className={styles.modalHeader}>
              <h3>确认订阅</h3>
              <button
                className={styles.modalClose}
                onClick={() => setShowPaymentModal(false)}
              >
                ✕
              </button>
            </div>

            <div className={styles.modalBody}>
              <div className={styles.orderSummary}>
                <div className={styles.orderItem}>
                  <span>方案</span>
                  <span>{plans.find(p => p.id === selectedPlan)?.name}</span>
                </div>
                <div className={styles.orderItem}>
                  <span>计费周期</span>
                  <span>{billingCycle === 'monthly' ? '月付' : '年付'}</span>
                </div>
                <div className={styles.orderTotal}>
                  <span>总计</span>
                  <span>¥{plans.find(p => p.id === selectedPlan)?.price[billingCycle]}/{billingCycle === 'monthly' ? '月' : '年'}</span>
                </div>
              </div>

              <div className={styles.paymentMethods}>
                <h4>选择支付方式</h4>
                <button className={styles.paymentMethod}>
                  💰 支付宝
                </button>
                <button className={styles.paymentMethod}>
                  💳 微信支付
                </button>
                <button className={styles.paymentMethod}>
                  🏦 银联/信用卡
                </button>
              </div>

              <div className={styles.mockWarning}>
                ⚠️ 这是演示环境，不会实际扣款
              </div>
            </div>

            <div className={styles.modalFooter}>
              <button
                className={styles.modalCancel}
                onClick={() => setShowPaymentModal(false)}
              >
                取消
              </button>
              <button
                className={styles.modalConfirm}
                onClick={handlePayment}
              >
                确认支付（Mock）
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
