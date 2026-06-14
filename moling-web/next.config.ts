import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  // 静态导出，用于 Docker Nginx 部署
  output: "export",
  // 禁用 Image Optimization（静态导出不支持）
  images: {
    unoptimized: true,
  },
  typescript: {
    // TODO: 逐步修复类型问题后移除该配置
    ignoreBuildErrors: true,
  },
};

export default nextConfig;
