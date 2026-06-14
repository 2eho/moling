'use client';

import { useState } from 'react';
import styles from './Landing.module.css';

export default function LandingPage() {
  const [menuOpen, setMenuOpen] = useState(false);

  return (
    <div className={styles.container}>
      {/* Header */}
      <header className={styles.header}>
        <div className={styles.headerInner}>
          <div className={styles.brand}>
            <span className={styles.brandName}>墨灵</span>
            <span className={styles.brandTagline}>AI 创作工作台</span>
          </div>

          <nav className={styles.nav}>
            <a href="#features" className={styles.navLink}>功能</a>
            <a href="#pricing" className={styles.navLink}>定价</a>
            <a href="#testimonials" className={styles.navLink}>评价</a>
            <a href="/auth/login" className={styles.navLink}>登录</a>
            <a href="/auth/register" className={styles.ctaBtn}>免费开始</a>
          </nav>

          <button
            className={styles.menuBtn}
            onClick={() => setMenuOpen(!menuOpen)}
          >
            ☰
          </button>
        </div>
      </header>

      {/* Mobile Menu */}
      {menuOpen && (
        <div className={styles.mobileMenu}>
          <a href="#features" className={styles.mobileLink}>功能</a>
          <a href="#pricing" className={styles.mobileLink}>定价</a>
          <a href="#testimonials" className={styles.mobileLink}>评价</a>
          <a href="/auth/login" className={styles.mobileLink}>登录</a>
          <a href="/auth/register" className={styles.mobileCta}>免费开始</a>
        </div>
      )}

      {/* Hero Section */}
      <section className={styles.hero}>
        <div className={styles.heroInner}>
          <h1 className={styles.heroTitle}>
            智能创作引擎
            <span className={styles.heroHighlight}>15秒</span>
            完成整章生成
          </h1>
          <p className={styles.heroSubtitle}>
            墨灵融合传统算法与 AI，为小说创作者提供前所未有的智能写作体验。
            从灵感捕捉到全文生成，一站式完成。
          </p>
          <div className={styles.heroActions}>
            <a href="/auth/register" className={styles.heroCtaPrimary}>
              免费开始 →
            </a>
            <a href="#demo" className={styles.heroCtaSecondary}>
              观看演示
            </a>
          </div>

          {/* 统计数据 */}
          <div className={styles.stats}>
            <div className={styles.statItem}>
              <div className={styles.statNumber}>10,000+</div>
              <div className={styles.statLabel}>活跃创作者</div>
            </div>
            <div className={styles.statItem}>
              <div className={styles.statNumber}>1M+</div>
              <div className={styles.statLabel}>生成章节</div>
            </div>
            <div className={styles.statItem}>
              <div className={styles.statNumber}>4.8</div>
              <div className={styles.statLabel}>用户评分</div>
            </div>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section id="features" className={styles.features}>
        <div className={styles.sectionInner}>
          <h2 className={styles.sectionTitle}>核心功能</h2>
          <p className={styles.sectionSubtitle}>
            专为小说创作者设计的智能工具集
          </p>

          <div className={styles.featureGrid}>
            <div className={styles.featureCard}>
              <div className={styles.featureIcon}>🎴</div>
              <h3 className={styles.featureTitle}>灵感卡牌系统</h3>
              <p className={styles.featureDesc}>
                独特的卡牌抽取机制，稳妥、有趣、惊艳三种方向，
                助您快速找到创作灵感。支持权重调节与多卡组合。
              </p>
            </div>

            <div className={styles.featureCard}>
              <div className={styles.featureIcon}>📚</div>
              <h3 className={styles.featureTitle}>四库管理体系</h3>
              <p className={styles.featureDesc}>
                人物、时间线、剧情承诺、世界观——四大知识库
                自动维护，确保故事连贯性与设定一致性。
              </p>
            </div>

            <div className={styles.featureCard}>
              <div className={styles.featureIcon}>🤖</div>
              <h3 className={styles.featureTitle}>AI 智能写作</h3>
              <p className={styles.featureDesc}>
                混合流水线引擎，传统算法处理结构，
                LLM 负责文采，15秒完成整章生成。
              </p>
            </div>

            <div className={styles.featureCard}>
              <div className={styles.featureIcon}>📖</div>
              <h3 className={styles.featureTitle}>剧情承诺追踪</h3>
              <p className={styles.featureDesc}>
                自动追踪伏笔、弧线、支线，智能提醒回收时机，
                让您的故事布局更加精妙。
              </p>
            </div>

            <div className={styles.featureCard}>
              <div className={styles.featureIcon}>⚙️</div>
              <h3 className={styles.featureTitle}>智能推荐系统</h3>
              <p className={styles.featureDesc}>
                Agent 实时分析写作上下文，提供个性化建议，
                让创作过程更加流畅自然。
              </p>
            </div>

            <div className={styles.featureCard}>
              <div className={styles.featureIcon}>📂</div>
              <h3 className={styles.featureTitle}>作品导入分析</h3>
              <p className={styles.featureDesc}>
                支持多种格式导入，自动分析角色、时间线、
                剧情承诺与世界观，快速建立知识库。
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* How it works */}
      <section className={styles.howItWorks}>
        <div className={styles.sectionInner}>
          <h2 className={styles.sectionTitle}>如何使用</h2>

          <div className={styles.steps}>
            <div className={styles.step}>
              <div className={styles.stepNumber}>1</div>
              <h3 className={styles.stepTitle}>创建项目</h3>
              <p className={styles.stepDesc}>
                新建小说项目，设置类型、简介等基本信息。
              </p>
            </div>

            <div className={styles.step}>
              <div className={styles.stepNumber}>2</div>
              <h3 className={styles.stepTitle}>导入或创建</h3>
              <p className={styles.stepDesc}>
                导入已有作品自动分析，或从零开始创建角色与世界观。
              </p>
            </div>

            <div className={styles.step}>
              <div className={styles.stepNumber}>3</div>
              <h3 className={styles.stepTitle}>抽取灵感</h3>
              <p className={styles.stepDesc}>
                抽取值感卡牌，选择创作方向，调节偏好权重。
              </p>
            </div>

            <div className={styles.step}>
              <div className={styles.stepNumber}>4</div>
              <h3 className={styles.stepTitle}>AI 生成</h3>
              <p className={styles.stepDesc}>
                点击生成，15秒内获得完整章节草稿，确认后即可使用。
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Testimonials */}
      <section id="testimonials" className={styles.testimonials}>
        <div className={styles.sectionInner}>
          <h2 className={styles.sectionTitle}>用户评价</h2>

          <div className={styles.testimonialGrid}>
            <div className={styles.testimonialCard}>
              <div className={styles.testimonialRating}>★★★★★</div>
              <p className={styles.testimonialText}>
                "墨灵彻底改变了我的创作流程。以前写一个章节需要半天，
                现在15秒就能得到高质量草稿，只需要微调即可。"
              </p>
              <div className={styles.testimonialAuthor}>
                <div className={styles.authorAvatar}>林</div>
                <div>
                  <div className={styles.authorName}>林作家</div>
                  <div className={styles.authorTitle}>网文作者 · 连载作品3部</div>
                </div>
              </div>
            </div>

            <div className={styles.testimonialCard}>
              <div className={styles.testimonialRating}>★★★★★</div>
              <p className={styles.testimonialText}>
                "四库管理功能太强了！自动追踪伏笔和剧情承诺，
                再也不用担心挖坑不填的问题。"
              </p>
              <div className={styles.testimonialAuthor}>
                <div className={styles.authorAvatar}>苏</div>
                <div>
                  <div className={styles.authorName}>苏编辑</div>
                  <div className={styles.authorTitle}>出版编辑 · 10年经验</div>
                </div>
              </div>
            </div>

            <div className={styles.testimonialCard}>
              <div className={styles.testimonialRating}>★★★★★</div>
              <p className={styles.testimonialText}>
                "灵感卡牌系统非常有创意，三种方向（稳妥/有趣/惊艳）
                让我能从不同角度思考剧情发展，打破了创作瓶颈。"
              </p>
              <div className={styles.testimonialAuthor}>
                <div className={styles.authorAvatar}>陈</div>
                <div>
                  <div className={styles.authorName}>陈写手</div>
                  <div className={styles.authorTitle}>剧本作家 · 影视改编</div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className={styles.ctaSection}>
        <div className={styles.sectionInner}>
          <h2 className={styles.ctaTitle}>准备好开始创作了吗？</h2>
          <p className={styles.ctaSubtitle}>
            加入 10,000+ 创作者的行列，体验 AI 辅助创作的魅力。
          </p>
          <a href="/auth/register" className={styles.ctaButton}>
            免费注册，立即开始 →
          </a>
        </div>
      </section>

      {/* Footer */}
      <footer className={styles.footer}>
        <div className={styles.footerInner}>
          <div className={styles.footerBrand}>
            <span className={styles.footerBrandName}>墨灵</span>
            <p className={styles.footerTagline}>AI 创作工作台</p>
          </div>

          <div className={styles.footerLinks}>
            <div className={styles.footerCol}>
              <h4 className={styles.footerColTitle}>产品</h4>
              <a href="#features" className={styles.footerLink}>功能介绍</a>
              <a href="#pricing" className={styles.footerLink}>定价方案</a>
              <a href="#demo" className={styles.footerLink}>演示视频</a>
            </div>

            <div className={styles.footerCol}>
              <h4 className={styles.footerColTitle}>支持</h4>
              <a href="#" className={styles.footerLink}>帮助中心</a>
              <a href="#" className={styles.footerLink}>联系我们</a>
              <a href="#" className={styles.footerLink}>反馈建议</a>
            </div>

            <div className={styles.footerCol}>
              <h4 className={styles.footerColTitle}>法律</h4>
              <a href="#" className={styles.footerLink}>隐私政策</a>
              <a href="#" className={styles.footerLink}>服务条款</a>
            </div>
          </div>
        </div>

        <div className={styles.footerBottom}>
          <p>© 2026 墨灵 · AI 创作工作台 · 保留所有权利</p>
        </div>
      </footer>
    </div>
  );
}
