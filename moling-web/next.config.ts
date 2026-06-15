import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  // 使用 standalone 模式，支持动态路由
  output: "standalone",
  // 子路径部署，配合宿主机 Nginx 的 /moling 反代
  basePath: "/moling",
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

  // 开启 SWC 压缩（生产环境默认开启，显式声明）
  swcMinify: true,

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

export default nextConfig;
