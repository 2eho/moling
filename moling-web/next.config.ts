import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  // Output as standalone for Docker deployment
  // output: "standalone",
  typescript: {
    ignoreBuildErrors: true,
  },
};

export default nextConfig;
