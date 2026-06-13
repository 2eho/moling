"use client";

import { useRouter } from "next/navigation";
import styles from "./LandingPage.module.css";

export function LandingPage() {
  const router = useRouter();

  return (
    <div className={styles.container}>
      {/* Navigation */}
      <nav className={styles.nav}>
        <div className={styles.navContent}>
          <div className={styles.logo}>
            <span className={styles.logoIcon}>✒</span>
            <span className={styles.logoText}>墨灵</span>
          </div>
          <div className={styles.navActions}>
            <button
              className={styles.loginBtn}
              onClick={() => router.push("/auth")}
            >
              登录
            </button>
            <button
              className={styles.signupBtn}
              onClick={() => router.push("/auth")}
            >
              开始创作
            </button>
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <section className={styles.hero}>
        <div className={styles.heroContent}>
          <h1 className={styles.heroTitle}>
            让 AI 成为你的
            <br />
            <span className={styles.gradient}>创作伙伴</span>
          </h1>
          <p className={styles.heroSubtitle}>
            墨灵是新一代 AI 驱动的小说创作平台
            <br />
            从灵感捕捉到成稿输出，全程智能辅助
          </p>
          <div className={styles.heroActions}>
            <button
              className={styles.primaryBtn}
              onClick={() => router.push("/auth")}
            >
              免费开始
            </button>
            <button className={styles.secondaryBtn}>
              观看演示
            </button>
          </div>
          <div className={styles.heroStats}>
            <div className={styles.statItem}>
              <span className={styles.statNumber}>10,000+</span>
              <span className={styles.statLabel}>创作者在使用</span>
            </div>
            <div className={styles.statDivider} />
            <div className={styles.statItem}>
              <span className={styles.statNumber}>50,000+</span>
              <span className={styles.statLabel}>小说正在创作</span>
            </div>
            <div className={styles.statDivider} />
            <div className={styles.statItem}>
              <span className={styles.statNumber}>98%</span>
              <span className={styles.statLabel}>用户满意度</span>
            </div>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section className={styles.features}>
        <div className={styles.sectionHeader}>
          <h2 className={styles.sectionTitle}>为什么选择墨灵？</h2>
          <p className={styles.sectionSubtitle}>
            我们重新定义了 AI 辅助创作的方式
          </p>
        </div>

        <div className={styles.featureGrid}>
          <div className={styles.featureCard}>
            <div className={styles.featureIcon}>🤖</div>
            <h3 className={styles.featureTitle}>AI 智能创作</h3>
            <p className={styles.featureDesc}>
              基于大语言模型的智能写作助手，帮你突破创作瓶颈，
              生成高质量的小说内容
            </p>
          </div>

          <div className={styles.featureCard}>
            <div className={styles.featureIcon}>👤</div>
            <h3 className={styles.featureTitle}>角色立体塑造</h3>
            <p className={styles.featureDesc}>
              从基本信息到深层性格，从外貌特征到人物关系，
              全方位塑造鲜活角色
            </p>
          </div>

          <div className={styles.featureCard}>
            <div className={styles.featureIcon}>🌍</div>
            <h3 className={styles.featureTitle}>世界观构建</h3>
            <p className={styles.featureDesc}>
              轻松创建复杂的历史背景、地理环境、魔法体系，
              让世界真实可信
            </p>
          </div>

          <div className={styles.featureCard}>
            <div className={styles.featureIcon}>📚</div>
            <h3 className={styles.featureTitle}>大纲智能生成</h3>
            <p className={styles.featureDesc}>
              AI 辅助生成小说大纲，支持多卷多章节结构，
              自动检查逻辑一致性
            </p>
          </div>

          <div className={styles.featureCard}>
            <div className={styles.featureIcon}>✍️</div>
            <h3 className={styles.featureTitle}>章节续写优化</h3>
            <p className={styles.featureDesc}>
              智能续写章节内容，支持风格模仿、情节推进、
              对话生成等多种模式
            </p>
          </div>

          <div className={styles.featureCard}>
            <div className={styles.featureIcon}>📊</div>
            <h3 className={styles.featureTitle}>创作数据分析</h3>
            <p className={styles.featureDesc}>
              实时统计字数、章节进度、写作习惯，
              用数据驱动创作效率
            </p>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className={styles.cta}>
        <div className={styles.ctaContent}>
          <h2 className={styles.ctaTitle}>准备开始你的创作之旅？</h2>
          <p className={styles.ctaSubtitle}>
            加入墨灵，让 AI 为你的创作赋能
          </p>
          <button
            className={styles.primaryBtn}
            onClick={() => router.push("/auth")}
          >
            免费注册
          </button>
        </div>
      </section>

      {/* Footer */}
      <footer className={styles.footer}>
        <div className={styles.footerContent}>
          <div className={styles.footerLogo}>
            <span className={styles.logoIcon}>✒</span>
            <span className={styles.logoText}>墨灵</span>
          </div>
          <p className={styles.footerText}>
            © 2024 墨灵 - AI 小说创作平台
          </p>
        </div>
      </footer>
    </div>
  );
}
