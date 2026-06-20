import { dirname } from "path";
import { fileURLToPath } from "url";
import { FlatCompat } from "@eslint/eslintrc";

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

const compat = new FlatCompat({
  baseDirectory: __dirname,
});

const eslintConfig = [
  ...compat.extends("next/core-web-vitals"),

  // 自定义规则覆盖
  {
    rules: {
      // ── React hooks（保持 error 级别） ──
      "react-hooks/rules-of-hooks": "error",

      // ── 代码质量 ──
      // 只禁止 console.log，保留 warn/error/info
      "no-console": ["warn", { allow: ["warn", "error", "info"] }],
    },
  },
];

export default eslintConfig;
