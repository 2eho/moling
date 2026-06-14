import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  // Output as standalone for Docker deployment
  // output: "standalone",
  typescript: {
    // TODO: 设置 ignoreBuildErrors: true 是因为当前项目存在 TypeScript 类型错误
    // 需要逐步修复类型问题后移除该配置
    // 追踪问题: 请查阅项目 issue 跟踪器中类型修复相关任务
    ignoreBuildErrors: true,
  },
};

export default nextConfig;
