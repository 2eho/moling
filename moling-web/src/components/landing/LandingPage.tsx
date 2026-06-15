"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { useRouter } from "next/navigation";
import styles from "./LandingPage.module.css";

// ========================================
// Mock 数据（根据 §6.8）
// ========================================

const HERO_DATA = {
  badge: "小说创作 Agent · 内测招募中",
  title: "每一次抽卡，都可能成就一个故事",
  highlightText: "抽卡",
  tagline: "灵感如墨，灵性如泉。让 AI 成为你的共笔之人，从灵感闪现到百万字长篇，一路相伴。",
  subtags: ["灵感抽卡", "轻输入 Agent", "四库记忆系统"],
  ctaLabel: "开始创作",
};

const STATS_DATA = [
  { value: "10,000+", label: "创作者入驻" },
  { value: "500万+", label: "累计生成字数" },
  { value: "92%", label: "日更完成率提升" },
];

const FEATURE_CARDS = [
  {
    icon: "抽卡",
    title: "抽卡出精品",
    description: "3 张章节灵感卡 × 4 种稀有度。支持单卡/双卡/全选组合生文，让每一次选择都充满惊喜。",
  },
  {
    icon: "生文",
    title: "你只管选择，AI 替你写",
    description: "默认自动推进，3 秒默许即确认。只需在关键节点做选择题，其余交给 AI 流畅完成。",
  },
  {
    icon: "四库",
    title: "永不遗忘的四库联动",
    description: "人物、时间线、剧情承诺、世界观四库联动，AI 自动维护一致性，杜绝遗忘和矛盾。",
  },
];

const GACHA_CARDS = [
  {
    id: "card1",
    rarity: "common" as const,
    type: "剧情",
    name: "暗巷相遇",
    description: "主角在雨夜暗巷中意外撞见关键人物",
  },
  {
    id: "card2",
    rarity: "rare" as const,
    type: "人物",
    name: "双面信使",
    description: "一个同时为两方传递消息的神秘角色",
  },
  {
    id: "card3",
    rarity: "epic" as const,
    type: "伏笔",
    name: "命轨交错",
    description: "三条看似无关的线索在高潮处汇合",
  },
  {
    id: "card4",
    rarity: "legendary" as const,
    type: "技法",
    name: "千面叙事",
    description: "同一事件从六个视角重述，真相层层剥开",
  },
];

const FLIP_CARDS = [
  {
    id: "flip1",
    rarity: "common" as const,
    icon: "⚔️",
    name: "初遇之章",
    backTitle: "普通 · 剧情卡",
    backDescription: "主角在市井中偶遇神秘旅者，一句预言改变命运轨迹。适合用作开篇引子或转折契机。",
  },
  {
    id: "flip2",
    rarity: "rare" as const,
    icon: "🌙",
    name: "月下密谋",
    backTitle: "稀有 · 人物卡",
    backDescription: "深夜的密室中，两个影子在月光下交织秘密。揭示隐藏的人物关系和未言明的动机。",
  },
  {
    id: "flip3",
    rarity: "epic" as const,
    icon: "🐉",
    name: "龙裔觉醒",
    backTitle: "史诗 · 伏笔卡",
    backDescription: "被封印千年的龙裔血脉在危机关头觉醒，天地变色，宿命齿轮开始转动。适合大高潮或转折点。",
  },
];

const TESTIMONIALS = [
  {
    initial: "林",
    name: "林夜",
    role: "起点签约作者 · 日更 4000 字",
    quote: "以前卡文能卡三天，现在抽一张剧情卡就破局了。AI 不是替代我写作，而是帮我打开思路的搭档。墨灵让我第一次感觉写作是享受而非折磨。",
  },
  {
    initial: "苏",
    name: "苏小棠",
    role: "晋江作者 · 言情 / 古言",
    quote: "三秒默许这个设计太懂网文作者了！手滑点到别的选项也不怕，它会等你确认。人物库自动维护角色关系图谱，再也不用担心 OOC。",
  },
  {
    initial: "陈",
    name: "陈墨白",
    role: "番茄小说作者 · 玄幻 / 仙侠",
    quote: "四库联动是真的香。写完十万字还能记得前面埋的伏笔，自动提醒我该回收哪个坑。世界观设定也不会前后矛盾，读者都说我这次写得特别严谨。",
  },
];

const FOOTER_LINKS = ["关于我们", "使用文档", "社区", "反馈"];

// ========================================
// 组件
// ========================================

export function LandingPage() {
  const router = useRouter();
  const [isMobile, setIsMobile] = useState(false);
  const [scrolled, setScrolled] = useState(false);
  const [flippedCards, setFlippedCards] = useState<Set<string>>(new Set());
  const [activeDot, setActiveDot] = useState(0);
  const [visibleElements, setVisibleElements] = useState<Set<string>>(new Set());

  const featuresSliderRef = useRef<HTMLDivElement>(null);
  const observerRef = useRef<IntersectionObserver | null>(null);

  // 检测移动端
  useEffect(() => {
    const checkMobile = () => {
      setIsMobile(window.innerWidth < 769);
    };
    checkMobile();
    window.addEventListener("resize", checkMobile);
    return () => window.removeEventListener("resize", checkMobile);
  }, []);

  // 滚动检测（Desktop Nav）
  useEffect(() => {
    if (isMobile) return;
    const handleScroll = () => {
      setScrolled(window.scrollY > 20);
    };
    window.addEventListener("scroll", handleScroll);
    return () => window.removeEventListener("scroll", handleScroll);
  }, [isMobile]);

  // Intersection Observer for scroll fade-in — 一次性注册，函数式更新避免闭包
  useEffect(() => {
    observerRef.current = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            setVisibleElements(prev => new Set(prev).add(entry.target.id));
          }
        });
      },
      { threshold: 0.15 }
    );

    const elements = document.querySelectorAll("[data-animate]");
    elements.forEach((el) => observerRef.current?.observe(el));

    return () => observerRef.current?.disconnect();
  }, []);

  // Mobile feature slider dot update
  const handleSliderScroll = useCallback(() => {
    if (!featuresSliderRef.current) return;
    const slider = featuresSliderRef.current;
    const card = slider.querySelector("[data-slide-card]");
    const cardWidth = (card as HTMLElement)?.offsetWidth || 1;
    const gap = 16;
    const scrollPos = slider.scrollLeft;
    const index = Math.round(scrollPos / (cardWidth + gap));
    setActiveDot(Math.min(index, 2));
  }, []);

  useEffect(() => {
    const slider = featuresSliderRef.current;
    if (!slider) return;
    const debounced = debounce(handleSliderScroll, 80);
    slider.addEventListener("scroll", debounced);
    return () => slider.removeEventListener("scroll", debounced);
  }, [handleSliderScroll]);

  // 翻转卡片
  const toggleFlip = (cardId: string) => {
    setFlippedCards((prev) => {
      const next = new Set(prev);
      if (next.has(cardId)) {
        next.delete(cardId);
      } else {
        next.add(cardId);
      }
      return next;
    });
  };

  // Desktop 试试手气
  const handleTryLuck = () => {
    setFlippedCards(new Set());
    setTimeout(() => {
      const randomIndex = Math.floor(Math.random() * GACHA_CARDS.length);
      const newSet = new Set<string>();
      newSet.add(GACHA_CARDS[randomIndex].id);
      setFlippedCards(newSet);
    }, 300);
  };

  // 导航点击滚动
  const scrollToSection = (id: string) => {
    const el = document.getElementById(id);
    el?.scrollIntoView({ behavior: "smooth" });
  };

  return (
    <>
      {/* ============================================ */}
      {/* Desktop Shell (≥769px)                      */}
      {/* ============================================ */}
      <div className={`${styles["desktop-shell"]} ${isMobile ? styles.hidden : ""}`}>
        {/* Desktop Nav */}
        <nav className={`${styles["d-nav"]} ${scrolled ? styles.scrolled : ""}`}>
          <div className={styles["d-nav-inner"]}>
            <div className={styles["d-nav-logo"]} onClick={() => window.scrollTo({ top: 0, behavior: "smooth" })}>
              <span className={styles["d-nav-logo-icon"]}>✒</span>
              <span className={styles["d-nav-logo-text"]}>墨灵</span>
            </div>
            <div className={styles["d-nav-links"]}>
              <a href="#features" onClick={(e) => { e.preventDefault(); scrollToSection("d-features"); }}>特性</a>
              <a href="#pricing" onClick={(e) => { e.preventDefault(); }}>定价</a>
              <a href="#testimonials" onClick={(e) => { e.preventDefault(); scrollToSection("d-testimonials"); }}>评价</a>
            </div>
            <button className={styles["d-nav-login"]} onClick={() => router.push("/auth")}>
              登录
            </button>
            <button className={styles["d-nav-cta"]} onClick={() => router.push("/auth")}>
              {HERO_DATA.ctaLabel}
            </button>
          </div>
        </nav>

        {/* Desktop Hero */}
        <section className={styles["d-hero"]} data-animate id="d-hero">
          {/* 浮动画装饰 */}
          <div className={`${styles["d-float-card"]} ${styles["fc1"]}`}>
            <div className={styles["d-float-card-inner"]}>📖</div>
          </div>
          <div className={`${styles["d-float-card"]} ${styles["fc2"]}`}>
            <div className={styles["d-float-card-inner"]}>✨</div>
          </div>
          <div className={`${styles["d-float-card"]} ${styles["fc3"]}`}>
            <div className={styles["d-float-card-inner"]}>🎴</div>
          </div>
          <div className={`${styles["d-float-card"]} ${styles["fc4"]}`}>
            <div className={styles["d-float-card-inner"]}>🖋️</div>
          </div>
          <div className={`${styles["d-float-card"]} ${styles["fc5"]}`}>
            <div className={styles["d-float-card-inner"]}>💡</div>
          </div>
          <div className={`${styles["d-float-card"]} ${styles["fc6"]}`}>
            <div className={styles["d-float-card-inner"]}>🌟</div>
          </div>

          <div className={styles["d-hero-content"]}>
            <div className={styles["d-hero-badge"]}>
              <span className={styles["d-hero-badge-dot"]} />
              {HERO_DATA.badge}
            </div>
            <h1 className={styles["d-hero-h1"]}>
              {HERO_DATA.title.split(HERO_DATA.highlightText)[0]}
              <span className={styles["d-highlight"]}>{HERO_DATA.highlightText}</span>
              {HERO_DATA.title.split(HERO_DATA.highlightText)[1]}
            </h1>
            <p className={styles["d-hero-subtitle"]}>{HERO_DATA.tagline}</p>
            <div className={styles["d-hero-subtags"]}>
              {HERO_DATA.subtags.map((tag, i) => (
                <span key={i} className={styles["d-hero-subtag"]}>{tag}</span>
              ))}
            </div>
            <div className={styles["d-hero-actions"]}>
              <button className={styles["d-hero-cta"]} onClick={() => router.push("/auth")}>
                {HERO_DATA.ctaLabel}
                <span className={styles["d-cta-glow"]} />
              </button>
            </div>
          </div>
        </section>

        {/* Desktop Stats */}
        <section className={styles["d-stats"]} data-animate id="d-stats">
          <div className={styles["d-stats-inner"]}>
            {STATS_DATA.map((stat, i) => (
              <div key={i} className={styles["d-stat-item"]}>
                <div className={styles["d-stat-value"]}>{stat.value}</div>
                <div className={styles["d-stat-label"]}>{stat.label}</div>
                {i < STATS_DATA.length - 1 && <div className={styles["d-stat-divider"]} />}
              </div>
            ))}
          </div>
        </section>

        {/* Desktop Features */}
        <section className={styles["d-features"]} data-animate id="d-features">
          <div className={styles["d-features-header"]}>
            <h2 className={styles["d-features-title"]}>为什么选择墨灵？</h2>
            <p className={styles["d-features-subtitle"]}>我们重新定义了 AI 辅助创作的方式</p>
          </div>
          <div className={styles["d-features-grid"]}>
            {FEATURE_CARDS.map((card, i) => (
              <div
                key={i}
                className={`${styles["d-feature-card"]} ${visibleElements.has("d-features") ? styles.visible : ""}`}
                style={{ transitionDelay: `${i * 120}ms` }}
              >
                <div className={styles["d-feature-icon"]}>
                  {card.icon === "抽卡" && (
                    <svg width="32" height="32" viewBox="0 0 32 32" fill="none">
                      <rect x="4" y="8" width="24" height="16" rx="3" stroke="currentColor" strokeWidth="1.5" />
                      <circle cx="16" cy="16" r="4" stroke="currentColor" strokeWidth="1.5" />
                      <path d="M16 12V8M16 24V20M12 16H8M24 16H20" stroke="currentColor" strokeWidth="1.5" />
                    </svg>
                  )}
                  {card.icon === "生文" && (
                    <svg width="32" height="32" viewBox="0 0 32 32" fill="none">
                      <path d="M8 6h16l-2 20H10L8 6z" stroke="currentColor" strokeWidth="1.5" />
                      <path d="M12 14h8M12 18h6" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
                    </svg>
                  )}
                  {card.icon === "四库" && (
                    <svg width="32" height="32" viewBox="0 0 32 32" fill="none">
                      <rect x="6" y="6" width="20" height="20" rx="3" stroke="currentColor" strokeWidth="1.5" />
                      <circle cx="16" cy="16" r="5" stroke="currentColor" strokeWidth="1.5" />
                      <path d="M16 6v6M16 20v6M6 16h6M20 16h6" stroke="currentColor" strokeWidth="1.5" />
                    </svg>
                  )}
                </div>
                <h3 className={styles["d-feature-title"]}>{card.title}</h3>
                <p className={styles["d-feature-desc"]}>{card.description}</p>
              </div>
            ))}
          </div>
        </section>

        {/* Desktop Gacha Preview */}
        <section className={styles["d-gacha"]} data-animate id="d-gacha">
          <div className={styles["d-gacha-header"]}>
            <h2 className={styles["d-gacha-title"]}>试试你的创作运气</h2>
            <p className={styles["d-gacha-subtitle"]}>每张灵感卡都有不同稀有度，组合使用可激发意想不到的剧情</p>
          </div>
          <div className={styles["d-gacha-grid"]}>
            {GACHA_CARDS.map((card) => (
              <div
                key={card.id}
                className={`${styles["d-gacha-card"]} ${styles[`rarity-${card.rarity}`] || ""} ${flippedCards.has(card.id) ? styles.flipped : ""}`}
                onClick={() => toggleFlip(card.id)}
                onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") toggleFlip(card.id); }}
                tabIndex={0}
                role="button"
                aria-label={`翻转卡片 ${card.name}`}
              >
                <div className={styles["d-gacha-card-inner"]}>
                  <div className={styles["d-gacha-card-front"]}>
                    <div className={styles["d-gacha-rarity"]}>{card.rarity === "common" ? "普通" : card.rarity === "rare" ? "稀有" : card.rarity === "epic" ? "史诗" : "传说"}</div>
                    <div className={styles["d-gacha-type"]}>{card.type}</div>
                    <div className={styles["d-gacha-name"]}>{card.name}</div>
                    <div className={styles["d-gacha-desc"]}>{card.description}</div>
                  </div>
                  <div className={styles["d-gacha-card-back"]}>
                    <div className={styles["d-gacha-back-icon"]}>🎴</div>
                    <div className={styles["d-gacha-back-text"]}>灵感</div>
                  </div>
                </div>
              </div>
            ))}
          </div>
          <button className={styles["d-gacha-try-btn"]} id="dGachaTryBtn" onClick={handleTryLuck}>
            试试手气
          </button>
        </section>

        {/* Desktop Testimonials */}
        <section className={styles["d-testimonials"]} data-animate id="d-testimonials">
          <div className={styles["d-testimonials-header"]}>
            <h2 className={styles["d-testimonials-title"]}>创作者们怎么说</h2>
            <p className={styles["d-testimonials-subtitle"]}>来自真实用户的评价</p>
          </div>
          <div className={styles["d-testimonials-grid"]}>
            {TESTIMONIALS.map((t, i) => (
              <div
                key={i}
                className={`${styles["d-testimonial-card"]} ${visibleElements.has("d-testimonials") ? styles.visible : ""}`}
                style={{ transitionDelay: `${i * 150}ms` }}
              >
                <div className={styles["d-testimonial-quote"]}>"{t.quote}"</div>
                <div className={styles["d-testimonial-author"]}>
                  <div className={styles["d-testimonial-avatar"]}>{t.initial}</div>
                  <div>
                    <div className={styles["d-testimonial-name"]}>{t.name}</div>
                    <div className={styles["d-testimonial-role"]}>{t.role}</div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </section>

        {/* Desktop CTA */}
        <section className={styles["d-cta"]} data-animate id="d-cta">
          <div className={styles["d-cta-card"]}>
            <h2 className={styles["d-cta-title"]}>准备开始你的创作之旅？</h2>
            <p className={styles["d-cta-subtitle"]}>加入墨灵，让 AI 为你的创作赋能</p>
            <button className={styles["d-cta-btn"]} onClick={() => router.push("/auth")}>
              免费注册
              <span className={styles["d-cta-glow"]} />
            </button>
          </div>
        </section>

        {/* Desktop Footer */}
        <footer className={styles["d-footer"]}>
          <div className={styles["d-footer-inner"]}>
            <div className={styles["d-footer-logo"]}>
              <span className={styles["d-footer-logo-icon"]}>✒</span>
              <span className={styles["d-footer-logo-text"]}>墨灵</span>
            </div>
            <div className={styles["d-footer-links"]}>
              {FOOTER_LINKS.map((link, i) => (
                <a key={i} href="#">{link}</a>
              ))}
            </div>
            <div className={styles["d-footer-copyright"]}>
              © 2025 墨灵 MoLing. All rights reserved.
            </div>
          </div>
        </footer>
      </div>

      {/* ============================================ */}
      {/* Mobile Shell (<769px)                      */}
      {/* ============================================ */}
      <div className={`${styles["mobile-shell"]} ${!isMobile ? styles.hidden : ""}`}>
        {/* Mobile Status Bar */}
        <div className={styles["m-status-bar"]}>
          <span className={styles["m-status-time"]} id="mStatusTime">9:41</span>
          <div className={styles["m-status-icons"]}>
            <span>📶</span>
            <span>🔋</span>
          </div>
        </div>

        {/* Mobile Phone Shell (429-768px) */}
        <div className={styles["m-phone-shell"]}>
          {/* Mobile Hero */}
          <section className={styles["m-hero"]}>
            <div className={styles["m-hero-floaters"]}>
              <span className={`${styles["m-floater"]} ${styles["mf1"]}`}>⚔️</span>
              <span className={`${styles["m-floater"]} ${styles["mf2"]}`}>🌙</span>
              <span className={`${styles["m-floater"]} ${styles["mf3"]}`}>🐉</span>
              <span className={`${styles["m-floater"]} ${styles["mf4"]}`}>✨</span>
            </div>
            <h1 className={styles["m-hero-title"]}>
              每一次抽卡，<br /><span className={styles["m-highlight"]}>都可能</span>成就<br />一个故事
            </h1>
            <p className={styles["m-hero-subtitle"]}>灵感如墨，灵性如泉</p>
            <button className={styles["m-cta-btn"]} onClick={() => router.push("/auth")}>
              {HERO_DATA.ctaLabel}
            </button>
          </section>

          {/* Mobile Stats */}
          <section className={styles["m-stats"]}>
            {STATS_DATA.map((stat, i) => (
              <div key={i} className={styles["m-stat-item"]}>
                <div className={styles["m-stat-value"]}>{stat.value}</div>
                <div className={styles["m-stat-label"]}>{stat.label}</div>
              </div>
            ))}
          </section>

          {/* Mobile Feature Slider */}
          <section className={styles["m-features"]}>
            <h2 className={styles["m-section-title"]}>核心能力</h2>
            <div className={styles["m-features-slider"]} ref={featuresSliderRef}>
              {FEATURE_CARDS.map((card, i) => (
                <div key={i} className={styles["m-feature-card"]} data-slide-card>
                  <div className={styles["m-feature-icon"]}>
                    {i === 0 && "🎴"}
                    {i === 1 && "✍️"}
                    {i === 2 && "📚"}
                  </div>
                  <h3 className={styles["m-feature-title"]}>
                    {i === 0 ? "灵感抽卡" : i === 1 ? "AI 替你写" : "四库记忆"}
                  </h3>
                  <p className={styles["m-feature-desc"]}>{card.description}</p>
                </div>
              ))}
            </div>
            <div className={styles["m-slider-dots"]}>
              {[0, 1, 2].map((dot) => (
                <span
                  key={dot}
                  className={`${styles["m-dot"]} ${activeDot === dot ? styles.active : ""}`}
                />
              ))}
            </div>
          </section>

          {/* Mobile Flip Cards */}
          <section className={styles["m-flip-cards"]}>
            <h2 className={styles["m-section-title"]}>翻转查看灵感</h2>
            <div className={styles["m-flip-cards-grid"]}>
              {FLIP_CARDS.map((card) => (
                <div
                  key={card.id}
                  className={`${styles["m-flip-card"]} ${flippedCards.has(card.id) ? styles.flipped : ""}`}
                  onClick={() => toggleFlip(card.id)}
                >
                  <div className={styles["m-flip-card-inner"]}>
                    <div className={styles["m-flip-card-front"]}>
                      <span className={styles["m-flip-icon"]}>{card.icon}</span>
                      <span className={styles["m-flip-name"]}>{card.name}</span>
                      <span className={styles["m-flip-hint"]}>点击翻转</span>
                    </div>
                    <div className={styles["m-flip-card-back"]}>
                      <div className={styles["m-flip-back-title"]}>{card.backTitle}</div>
                      <div className={styles["m-flip-back-desc"]}>{card.backDescription}</div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </section>

          {/* Mobile CTA */}
          <section className={styles["m-cta"]}>
            <button className={styles["m-cta-full"]} onClick={() => router.push("/auth")}>
              {HERO_DATA.ctaLabel}
            </button>
            <p className={styles["m-cta-hint"]}>无需注册，即刻开始你的创作之旅</p>
          </section>

          {/* Mobile Bottom Nav */}
          <nav className={styles["m-bottom-nav"]}>
            <button className={`${styles["m-nav-item"]} ${styles.active}`}>
              <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" />
                <polyline points="9 22 9 12 15 12 15 22" />
              </svg>
              <span>首页</span>
            </button>
            <button className={styles["m-nav-item"]} onClick={() => router.push("/projects")}>
              <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                <polyline points="14 2 14 8 20 8" />
              </svg>
              <span>作品</span>
            </button>
            <button className={styles["m-nav-item"]}>
              <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M12 20h9" />
                <path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z" />
              </svg>
              <span>创作</span>
            </button>
            <button className={styles["m-nav-item"]} onClick={() => router.push("/settings")}>
              <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
                <circle cx="12" cy="7" r="4" />
              </svg>
              <span>我的</span>
            </button>
          </nav>

          {/* Home Indicator */}
          <div className={styles["m-home-indicator"]} />
        </div>
      </div>
    </>
  );
}

// debounce 辅助函数
function debounce<T extends (...args: unknown[]) => void>(fn: T, ms: number): (...args: Parameters<T>) => void {
  let timer: ReturnType<typeof setTimeout>;
  return (...args: Parameters<T>) => {
    clearTimeout(timer);
    timer = setTimeout(() => fn(...args), ms);
  };
}
