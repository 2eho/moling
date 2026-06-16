import type { NextConfig } from "next";
import { withSentryConfig } from "@sentry/nextjs";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  // 使用 standalone 模式，支持动态路由
  // output: "standalone", // 临时禁用，修复复制错误
  // 子路径部署，配合宿主机 Nginx 的 /moling 反代
  basePath: "/moling",
  
  // 修复多lockfile警告和构建错误
  outputFileTracingRoot: process.cwd(),
  // 禁用 Image Optimization（standalone 模式可选）
  images: {
    unoptimized: true,
  },
  typescript: {
    // TODO: 逐步修复类型问题后移除该配置
    ignoreBuildErrors: true,
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
};

export default withSentryConfig(nextConfig, {
  // Sentry 配置
  org: "moling",
  project: "moling-web",
  
  // 仅在 CI 环境中输出版本信息
  silent: !process.env.CI,
  
  // 自动上传 Source Maps 到 Sentry
  widenClientFileUpload: true,
  
  // 自动包装 App Router 的路由
  automaticVercelMonitors: true,
  
  // 禁用 Sentry 遥测
  telemetry: false,
});
