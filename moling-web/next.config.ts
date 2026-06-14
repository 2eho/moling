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
};

export default nextConfig;
