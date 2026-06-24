import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "path";

const isAnalyze = process.env.BUILD_ANALYZE === "true";

// Conditionally load the bundle analyzer
const plugins: ReturnType<typeof defineConfig>["plugins"] = [react()];
if (isAnalyze) {
  const { visualizer } = await import("rollup-plugin-visualizer");
  plugins.push(
    visualizer({
      open: true,
      filename: "dist/stats.html",
      gzipSize: true,
      brotliSize: true,
      template: "treemap",
    }),
  );
}

export default defineConfig({
  plugins,
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "../packages/ui/src"),
    },
  },
  server: {
    port: 3000,
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: "dist",
    sourcemap: true,
    target: "esnext",
    minify: "esbuild",
    cssCodeSplit: true,
    rollupOptions: {
      // All @tauri-apps/* imports are provided by the Tauri webview
      // at runtime (via `withGlobalTauri: true`). They must not be
      // bundled into the Vite output.
      external: [
        "@tauri-apps/api/core",
        "@tauri-apps/api/event",
        "@tauri-apps/plugin-dialog",
        "@tauri-apps/plugin-notification",
        "@tauri-apps/plugin-shell",
        "@tauri-apps/plugin-fs",
        "@tauri-apps/plugin-clipboard-manager",
        "@tauri-apps/plugin-global-shortcut",
      ],
      output: {
        manualChunks: {
          "vendor-react": ["react", "react-dom", "react-router-dom"],
          "vendor-query": ["@tanstack/react-query"],
          "vendor-ui": [
            "@radix-ui/react-avatar",
            "@radix-ui/react-dialog",
            "@radix-ui/react-dropdown-menu",
            "@radix-ui/react-label",
            "@radix-ui/react-popover",
            "@radix-ui/react-scroll-area",
            "@radix-ui/react-select",
            "@radix-ui/react-separator",
            "@radix-ui/react-slot",
            "@radix-ui/react-switch",
            "@radix-ui/react-tabs",
            "@radix-ui/react-toast",
            "@radix-ui/react-tooltip",
          ],
          "vendor-icons": ["lucide-react"],
          "vendor-utils": ["zustand", "clsx", "tailwind-merge", "class-variance-authority"],
        },
      },
    },
  },
});
