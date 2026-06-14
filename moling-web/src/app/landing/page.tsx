'use client';

import { useState, useEffect } from 'react';
import styles from './Landing.module.css';

export default function LandingPage() {
  const [menuOpen, setMenuOpen] = useState(false);
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const handleScroll = () => setScrolled(window.scrollY > 20);
    window.addEventListener('scroll', handleScroll, { passive: true });
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  return (
    <div className={styles.page}>
      {/* ── Fixed Navigation ── */}
      <nav
        className={`${styles.nav} ${scrolled ? styles.navScrolled : ''}`}
        role="navigation"
        aria-label="主导航"
      >
        <div className={styles.navInner}>
          <a href="/" className={styles.navBrand} aria-label="墨灵首页">
            {/* Logo SVG */}
            <svg
              className={styles.navLogo}
              viewBox="0 0 32 32"
              fill="none"
              xmlns="http://www.w3.org/2000/svg"
              aria-hidden="true"
            >
              <circle cx="16" cy="16" r="14" fill="none" stroke="#6366f1" strokeWidth="1.5" opacity="0.3" />
              <path
                d="M16 6C16 6 10 14 10 20C10 23.3 12.7 26 16 26C19.3 26 22 23.3 22 20C22 14 16 6 16 6Z"
                fill="#6366f1"
                opacity="0.8"
              />
              <path d="M16 10L20 22" stroke="#d4a843" strokeWidth="1.5" strokeLinecap="round" />
              <circle cx="16" cy="22" r="1.5" fill="#d4a843" />
            </svg>
            <span className={styles.navTitle}>
              墨<span className={styles.navTitleAccent}>灵</span>
            </span>
          </a>

          <ul className={styles.navLinks}>
            <li><a href="#features" className={styles.navLink}>核心功能</a></li>
            <li><a href="#gacha" className={styles.navLink}>灵感抽卡</a></li>
            <li><a href="#testimonials" className={styles.navLink}>作者评价</a></li>
            <li><a href="/auth" className={styles.navLink}>登录</a></li>
            <li>
              <a href="/auth" className={styles.navCta}>免费开始</a>
            </li>
          </ul>

          <button
            className={styles.menuBtn}
            onClick={() => setMenuOpen(!menuOpen)}
            aria-label="切换菜单"
          >
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
              <line x1="3" y1="6" x2="21" y2="6" />
              <line x1="3" y1="12" x2="21" y2="12" />
              <line x1="3" y1="18" x2="21" y2="18" />
            </svg>
          </button>
        </div>

        {/* Mobile Menu */}
        {menuOpen && (
          <div className={styles.mobileMenu}>
            <a href="#features" className={styles.mobileLink} onClick={() => setMenuOpen(false)}>核心功能</a>
            <a href="#gacha" className={styles.mobileLink} onClick={() => setMenuOpen(false)}>灵感抽卡</a>
            <a href="#testimonials" className={styles.mobileLink} onClick={() => setMenuOpen(false)}>作者评价</a>
            <a href="/auth" className={styles.mobileLink} onClick={() => setMenuOpen(false)}>登录</a>
            <a href="/auth" className={styles.mobileCta} onClick={() => setMenuOpen(false)}>免费开始</a>
          </div>
        )}
      </nav>

      {/* ── Hero Section ── */}
      <section className={styles.hero} id="main">
        <div className={styles.heroBg} />

        {/* Floating Cards */}
        <div className={styles.heroFloatingCards} aria-hidden="true">
          <div className={styles.floatingCard} />
          <div className={`${styles.floatingCard} ${styles.floatingCard2}`} />
          <div className={`${styles.floatingCard} ${styles.floatingCard3}`} />
          <div className={`${styles.floatingCard} ${styles.floatingCard4}`} />
          <div className={`${styles.floatingCard} ${styles.floatingCard5}`} />
          <div className={`${styles.floatingCard} ${styles.floatingCard6}`} />
        </div>

        <div className={styles.heroContent}>
          {/* Badge */}
          <div className={styles.heroBadge}>
            <span className={styles.heroBadgeDot} />
            <span>AI 驱动的创意写作引擎</span>
          </div>

          {/* Title */}
          <h1 className={styles.heroTitle}>
            每一次抽卡，
            <br />
            都<span className={styles.heroHighlight}>可能成就</span>一个故事
          </h1>

          {/* Tagline */}
          <p className={styles.heroTagline}>
            灵感抽卡 · 多卡组合 · 四库记忆 · 智能创作
          </p>

          {/* Feature Tags */}
          <div className={styles.heroSubtags}>
            <span className={styles.heroSubtag}>
              <span className={styles.subtagIcon}>
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M12 20h9M16.5 3.5a2.12 2.12 0 013 3L7 19l-4 1 1-4L16.5 3.5z"/></svg>
              </span>
              小说创作Agent
            </span>
            <span className={styles.heroSubtag}>
              <span className={styles.subtagIcon}>
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><rect x="3" y="3" width="18" height="18" rx="2"/><path d="M3 9h18M9 3v18"/></svg>
              </span>
              抽卡生文
            </span>
            <span className={styles.heroSubtag}>
              <span className={styles.subtagIcon}>
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M4 19.5A2.5 2.5 0 016.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 014 19.5v-15A2.5 2.5 0 016.5 2z"/></svg>
              </span>
              四库记忆
            </span>
          </div>

          {/* CTA */}
          <a href="/auth" className={styles.heroCta}>
            开始创作
            <svg
              className={styles.heroCtaArrow}
              width="18"
              height="18"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2.5"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="M5 12h14M12 5l7 7-7 7" />
            </svg>
          </a>
        </div>
      </section>

      {/* ── Features Section ── */}
      <section id="features" className={styles.features}>
        <div className={styles.sectionInner}>
          <div className={styles.sectionHeader}>
            <p className={styles.sectionLabel}>核心能力</p>
            <h2 className={styles.sectionTitle}>
              为小说创作者打造
            </h2>
          </div>

          <div className={styles.featuresGrid}>
            {/* Feature 1 */}
            <div className={styles.featureCard}>
              <div className={`${styles.featureIconWrap} ${styles.featureIconAmber}`}>
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M12 20h9M16.5 3.5a2.12 2.12 0 013 3L7 19l-4 1 1-4L16.5 3.5z" />
                </svg>
              </div>
              <h3 className={styles.featureTitle}>灵感抽卡</h3>
              <p className={styles.featureDesc}>
                抽取灵感卡牌，获取章节方向与情节转折。每次抽卡都是一次与灵感的邂逅，让创作不再空白。
              </p>
            </div>

            {/* Feature 2 */}
            <div className={styles.featureCard}>
              <div className={`${styles.featureIconWrap} ${styles.featureIconIndigo}`}>
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <rect x="2" y="3" width="20" height="14" rx="2" />
                  <path d="M8 21h8M12 17v4" />
                </svg>
              </div>
              <h3 className={styles.featureTitle}>AI 生文</h3>
              <p className={styles.featureDesc}>
                多张卡牌组合，AI 智能编织连贯剧情。卡牌越稀有，生成越惊艳，让文字流淌出你想要的故事。
              </p>
            </div>

            {/* Feature 3 */}
            <div className={styles.featureCard}>
              <div className={`${styles.featureIconWrap} ${styles.featureIconGreen}`}>
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M4 19.5A2.5 2.5 0 016.5 17H20" />
                  <path d="M6.5 2H20v20H6.5A2.5 2.5 0 014 19.5v-15A2.5 2.5 0 016.5 2z" />
                </svg>
              </div>
              <h3 className={styles.featureTitle}>四库记忆</h3>
              <p className={styles.featureDesc}>
                人物库 · 时间线 · 剧情承诺 · 世界观四库联动，确保长篇叙事的一致性与深度，永不矛盾。
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* ── Gacha Preview Section ── */}
      <section id="gacha" className={styles.gachaSection}>
        <div className={styles.sectionInner}>
          <div className={styles.sectionHeader}>
            <p className={styles.sectionLabel}>灵感卡牌</p>
            <h2 className={styles.sectionTitle}>
              抽一张属于你的故事卡牌
            </h2>
          </div>

          <div className={styles.gachaCards}>
            {/* Card 1 — N (Ordinary) */}
            <div className={styles.gachaCardOuter}>
              <div className={`${styles.gachaCard} ${styles.gachaCardCommon}`}>
                <div className={styles.gachaCardFront}>
                  <div className={styles.gachaCardType}>N · 普通</div>
                  <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                    <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5" />
                  </svg>
                  <div className={styles.gachaCardName}>初遇之章</div>
                  <div className={styles.gachaCardRarity}>COMMON</div>
                </div>
              </div>
              <p className={styles.gachaCardHint}>主角在市井中偶遇神秘旅者</p>
            </div>

            {/* Card 2 — R (Rare) */}
            <div className={styles.gachaCardOuter}>
              <div className={`${styles.gachaCard} ${styles.gachaCardRare}`}>
                <div className={styles.gachaCardFront}>
                  <div className={styles.gachaCardType}>R · 稀有</div>
                  <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                    <path d="M21 12.79A9 9 0 1111.21 3 7 7 0 0021 12.79z" />
                  </svg>
                  <div className={styles.gachaCardName}>月下密谋</div>
                  <div className={styles.gachaCardRarity}>RARE</div>
                </div>
              </div>
              <p className={styles.gachaCardHint}>两个影子在月光下交织</p>
            </div>

            {/* Card 3 — SR (Epic) */}
            <div className={styles.gachaCardOuter}>
              <div className={`${styles.gachaCard} ${styles.gachaCardEpic}`}>
                <div className={styles.gachaCardFront}>
                  <div className={styles.gachaCardType}>SR · 史诗</div>
                  <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                    <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z" />
                  </svg>
                  <div className={styles.gachaCardName}>龙裔觉醒</div>
                  <div className={styles.gachaCardRarity}>EPIC</div>
                </div>
              </div>
              <p className={styles.gachaCardHint}>被封印千年的龙裔血脉觉醒</p>
            </div>
          </div>

          <div className={styles.gachaCta}>
            <a href="/auth" className={styles.gachaTryBtn}>
              试抽一张
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><path d="M5 12h14M12 5l7 7-7 7"/></svg>
            </a>
            <p className={styles.gachaHint}>每日免费 3 次 · 无需注册</p>
          </div>
        </div>
      </section>

      {/* ── Stats / Social Proof Section ── */}
      <section id="testimonials" className={styles.socialProof}>
        <div className={styles.sectionInner}>
          <div className={styles.sectionHeader}>
            <p className={styles.sectionLabel}>创作者社区</p>
            <h2 className={styles.sectionTitle}>
              被万千作者信赖
            </h2>
          </div>

          <div className={styles.statsRow}>
            <div className={styles.statItem}>
              <div className={styles.statValue}>10,000+</div>
              <div className={styles.statLabel}>创作者入驻</div>
            </div>
            <div className={styles.statItem}>
              <div className={styles.statValue}>500万+</div>
              <div className={styles.statLabel}>累计创作字数</div>
            </div>
            <div className={styles.statItem}>
              <div className={styles.statValue}>92%</div>
              <div className={styles.statLabel}>日更完成率提升</div>
            </div>
          </div>

          <div className={styles.testimonials}>
            <div className={styles.testimonialCard}>
              <div className={styles.testimonialQuote}>
                墨灵彻底改变了我的创作流程。以前写一个章节需要半天，现在15秒就能得到高质量草稿，只需要微调即可。
              </div>
              <div className={styles.testimonialAuthor}>
                <div className={styles.testimonialAvatar}>林</div>
                <div>
                  <div className={styles.testimonialName}>林作家</div>
                  <div className={styles.testimonialRole}>网文作者 · 连载作品3部</div>
                </div>
              </div>
            </div>

            <div className={styles.testimonialCard}>
              <div className={styles.testimonialQuote}>
                四库管理功能太强了！自动追踪伏笔和剧情承诺，再也不用担心挖坑不填的问题，长篇创作终于有了保障。
              </div>
              <div className={styles.testimonialAuthor}>
                <div className={styles.testimonialAvatar}>苏</div>
                <div>
                  <div className={styles.testimonialName}>苏编辑</div>
                  <div className={styles.testimonialRole}>出版编辑 · 10年经验</div>
                </div>
              </div>
            </div>

            <div className={styles.testimonialCard}>
              <div className={styles.testimonialQuote}>
                灵感卡牌系统非常有创意，三种方向让我能从不同角度思考剧情发展，打破了创作瓶颈，每次抽卡都充满期待。
              </div>
              <div className={styles.testimonialAuthor}>
                <div className={styles.testimonialAvatar}>陈</div>
                <div>
                  <div className={styles.testimonialName}>陈写手</div>
                  <div className={styles.testimonialRole}>剧本作家 · 影视改编</div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ── Final CTA Section ── */}
      <section className={styles.ctaSection}>
        <div className={styles.ctaInner}>
          <h2 className={styles.ctaTitle}>准备好开始创作了吗？</h2>
          <p className={styles.ctaDesc}>
            加入万千创作者的行列，用 AI 的力量释放你的想象力。
          </p>
          <a href="/auth" className={styles.ctaButton}>
            免费开始体验
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <path d="M5 12h14M12 5l7 7-7 7" />
            </svg>
          </a>
        </div>
      </section>

      {/* ── Footer ── */}
      <footer className={styles.footer}>
        <div className={styles.footerInner}>
          <div className={styles.footerBrand}>
            <svg className={styles.footerLogo} viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
              <circle cx="16" cy="16" r="14" fill="none" stroke="#6366f1" strokeWidth="1.5" opacity="0.3" />
              <path d="M16 6C16 6 10 14 10 20C10 23.3 12.7 26 16 26C19.3 26 22 23.3 22 20C22 14 16 6 16 6Z" fill="#6366f1" opacity="0.8" />
              <path d="M16 10L20 22" stroke="#d4a843" strokeWidth="1.5" strokeLinecap="round" />
              <circle cx="16" cy="22" r="1.5" fill="#d4a843" />
            </svg>
            <span className={styles.footerTitle}>墨<span className={styles.footerTitleAccent}>灵</span></span>
          </div>

          <ul className={styles.footerLinks}>
            <li><a href="#features">核心功能</a></li>
            <li><a href="#gacha">灵感抽卡</a></li>
            <li><a href="#testimonials">作者评价</a></li>
          </ul>

          <p className={styles.footerCopy}>&copy; 2026 墨灵 MoLing. All rights reserved.</p>
        </div>
      </footer>
    </div>
  );
}
