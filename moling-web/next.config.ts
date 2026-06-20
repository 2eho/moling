import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  // 子路径部署，配合宿主机 Nginx 的 /moling 反代
  basePath: "/moling",
  // 使用 standalone 输出模式
  output: "standalone",
  // ESLint 检查
  eslint: {
    // Phase 2 完成：ESLint 配置已修复，使用 eslint.config.mjs flat config
    ignoreDuringBuilds: false,
  },
  // 禁用 Image Optimization（standalone 模式可选）
  images: {
    unoptimized: true,
  },
  typescript: {
    ignoreBuildErrors: false,
  },

  // ═══════════════════════════════════════════════════════════
  // 性能优化配置
  // ═══════════════════════════════════════════════════════════

  // 注意: Next.js 15 中 SWC 压缩默认开启，无需显式配置
  // 如需禁用: swcMinify: false (Next.js 14 兼容项已移除)

  // 移除 X-Powered-By 响应头，提高安全性
  poweredByHeader: false,

  // 生产环境编译时移除 console.log / console.debug
  compiler: {
    removeConsole:
      process.env.NODE_ENV === "production"
        ? { exclude: ["error", "warn"] }
        : false,
  },

  // HTTP keep-alive 连接复用（减少 API 请求的 TCP 握手开销）
  httpAgentOptions: {
    keepAlive: true,
  },

  // 禁用 ETag 生成，配合 Nginx 的强缓存策略
  generateEtags: false,

  // 在页面初始加载时预加载关键 JS/CSS chunk
  experimental: {
    // 优化初始加载时的关键 CSS
    optimizeCss: false, // 需要 critters 依赖，暂时关闭
    // 优化服务器端 React DOM 操作
    webVitalsAttribution: ["CLS", "LCP", "FID"],
  },

  // ═══════════════════════════════════════════════════════════
  // 开发模式 API 代理
  // ═══════════════════════════════════════════════════════════
  // 在 dev 模式下，Next.js dev server 会将 /moling/api/* 请求
  // 转发到后端 FastAPI（避免跨域和 404 问题）
  // 生产环境由 Nginx 处理反代，此配置不生效
  // ═══════════════════════════════════════════════════════════
  // ═══════════════════════════════════════════════════════════
  // 根路径重定向
  // ═══════════════════════════════════════════════════════════
  async redirects() {
    return [
      {
        source: '/',
        destination: '/moling',
        basePath: false,
        permanent: false,
      },
    ];
  },

  rewrites: async () => [
    {
      source: "/api/:path*",
      destination: "http://127.0.0.1:8000/api/:path*",
    },
  ],
};

export default nextConfig;
